#!/usr/bin/env python3
"""Live dashboard server for Claude Code projects.

Serves the dashboard on http://localhost:8420 and auto-refreshes
when files change in ~/.claude/projects/.

Usage:
    python3 claude-dashboard-server.py
    python3 claude-dashboard-server.py --port 9000
"""

import json
import os
import sys
import time
import threading
import hashlib
from http.server import HTTPServer, BaseHTTPRequestHandler
from pathlib import Path
from datetime import datetime

PROJECTS_DIR = Path.home() / ".claude" / "projects"
DEFAULT_PORT = 8420
POLL_INTERVAL = 3  # seconds


# --- Data extraction (same as claude-dashboard.py) ---

def dirname_to_path(dirname):
    """Convert a project dirname back to a filesystem path."""
    return "/" + dirname.lstrip("-").replace("-", "/")


def read_claude_md(path):
    """Read a CLAUDE.md file, returning its content or None."""
    claude_md = Path(path) / "CLAUDE.md"
    if claude_md.exists():
        try:
            return claude_md.read_text(errors="replace")[:8000]
        except Exception:
            return None
    return None


def find_claude_md(dirname):
    return read_claude_md(dirname_to_path(dirname))


def extract_memory_files(project_path):
    memory_dir = project_path / "memory"
    files = []
    if memory_dir.is_dir():
        for mem_file in sorted(memory_dir.iterdir()):
            if mem_file.is_file() and not mem_file.name.startswith("."):
                try:
                    content = mem_file.read_text(errors="replace")
                    files.append({"name": mem_file.name, "content": content[:5000]})
                except Exception:
                    continue
    return files


def extract_sessions(project_path):
    sessions = []
    for jsonl_file in sorted(project_path.glob("*.jsonl")):
        session_id = jsonl_file.stem
        first_user_msg = ""
        user_messages = []
        timestamp = ""
        last_timestamp = ""
        msg_count = 0
        try:
            with open(jsonl_file, "r") as f:
                for line in f:
                    try:
                        d = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    if d.get("type") == "user" and d.get("message", {}).get("role") == "user":
                        msg_count += 1
                        content = d["message"].get("content", "")
                        text = ""
                        if isinstance(content, str):
                            text = content.strip()
                        elif isinstance(content, list):
                            for c in content:
                                if isinstance(c, dict) and c.get("type") == "text":
                                    text = c["text"].strip()
                                    break
                        if text:
                            if not first_user_msg:
                                first_user_msg = text[:300]
                            user_messages.append(text[:200])
                        if not timestamp and d.get("timestamp"):
                            timestamp = d["timestamp"]
                    if d.get("timestamp"):
                        last_timestamp = d["timestamp"]
        except Exception:
            continue
        if first_user_msg or timestamp:
            sessions.append({
                "id": session_id,
                "first_message": first_user_msg or "(no message)",
                "user_messages": user_messages,
                "started": timestamp,
                "last_activity": last_timestamp,
                "message_count": msg_count,
            })
    sessions.sort(key=lambda s: s.get("started", ""), reverse=True)
    return sessions


def project_display_name(dirname):
    """Convert project dirname to readable path like ~/ws/jira.

    Detects the home directory prefix (e.g. /Users/<user> or /home/<user>)
    and replaces it with ~.
    """
    home = str(Path.home())
    # dirname format: -Users-alice-ws-jira -> path /Users/alice/ws/jira
    # We find where the home dir prefix ends in the dirname
    home_prefix = "-" + home.lstrip("/").replace("/", "-")
    if dirname.startswith(home_prefix):
        rest = dirname[len(home_prefix):]
        if not rest:
            return "~"
        # rest starts with "-", split into path components
        return "~/" + rest.lstrip("-").replace("-", "/")
    return dirname


def format_date(iso_str):
    if not iso_str:
        return ""
    try:
        dt = datetime.fromisoformat(iso_str.replace("Z", "+00:00"))
        return dt.strftime("%Y-%m-%d %H:%M")
    except Exception:
        return iso_str[:16]


def collect_data():
    projects_data = []
    if not PROJECTS_DIR.is_dir():
        return projects_data
    for project_dir in sorted(PROJECTS_DIR.iterdir()):
        if not project_dir.is_dir():
            continue
        name = project_display_name(project_dir.name)
        sessions = extract_sessions(project_dir)
        memory_files = extract_memory_files(project_dir)
        claude_md = find_claude_md(project_dir.name)
        for s in sessions:
            s["started"] = format_date(s["started"])
            s["last_activity"] = format_date(s["last_activity"])
        projects_data.append({
            "name": name,
            "dirname": project_dir.name,
            "sessions": sessions,
            "has_memory": len(memory_files) > 0,
            "memory_files": memory_files,
            "claude_md": claude_md,
        })
    projects_data.sort(key=lambda p: len(p["sessions"]), reverse=True)
    return projects_data


# --- File change detection ---

def get_dir_fingerprint():
    """Get a hash of mtimes of all relevant files to detect changes."""
    parts = []
    try:
        for project_dir in sorted(PROJECTS_DIR.iterdir()):
            if not project_dir.is_dir():
                continue
            for f in project_dir.glob("*.jsonl"):
                try:
                    parts.append(f"{f}:{f.stat().st_mtime}")
                except OSError:
                    pass
            mem_dir = project_dir / "memory"
            if mem_dir.is_dir():
                for f in mem_dir.iterdir():
                    try:
                        parts.append(f"{f}:{f.stat().st_mtime}")
                    except OSError:
                        pass
            # Check CLAUDE.md in project dir
            real_path = "/" + project_dir.name.lstrip("-").replace("-", "/")
            claude_md = Path(real_path) / "CLAUDE.md"
            if claude_md.exists():
                try:
                    parts.append(f"{claude_md}:{claude_md.stat().st_mtime}")
                except OSError:
                    pass
    except Exception:
        pass
    return hashlib.md5("|".join(parts).encode()).hexdigest()


# --- Shared state ---

class DashboardState:
    def __init__(self):
        self.lock = threading.Lock()
        self.data_json = "[]"
        self.version = 0
        self.refresh()

    def refresh(self):
        data = collect_data()
        with self.lock:
            self.data_json = json.dumps(data)
            self.version += 1

    def get(self):
        with self.lock:
            return self.data_json, self.version


state = None


def get_state():
    global state
    if state is None:
        state = DashboardState()
    return state


def watcher_thread():
    """Poll for file changes and refresh data."""
    last_fp = get_dir_fingerprint()
    while True:
        time.sleep(POLL_INTERVAL)
        try:
            fp = get_dir_fingerprint()
            if fp != last_fp:
                last_fp = fp
                get_state().refresh()
                print(f"[{datetime.now().strftime('%H:%M:%S')}] Data refreshed (v{get_state().get()[1]})")
        except Exception as e:
            print(f"Watcher error: {e}")


# --- HTML template ---

def get_html():
    return """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Claude Code Dashboard</title>
<style>
  :root {
    --bg: #0f1117;
    --surface: #1a1d27;
    --surface2: #232733;
    --border: #2d3140;
    --text: #e4e6ef;
    --text-dim: #8b8fa3;
    --accent: #d4a574;
    --accent2: #7c9dd4;
    --accent3: #8bc4a0;
    --search-bg: #1e2130;
  }
  * { margin: 0; padding: 0; box-sizing: border-box; }
  body {
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', system-ui, sans-serif;
    background: var(--bg);
    color: var(--text);
    min-height: 100vh;
  }
  .header {
    padding: 24px 32px;
    border-bottom: 1px solid var(--border);
    display: flex;
    align-items: center;
    gap: 16px;
    flex-wrap: wrap;
    position: sticky;
    top: 0;
    background: var(--bg);
    z-index: 100;
  }
  .header h1 {
    font-size: 22px;
    font-weight: 600;
    color: var(--accent);
    white-space: nowrap;
  }
  .header .stats {
    color: var(--text-dim);
    font-size: 14px;
  }
  .live-dot {
    display: inline-block;
    width: 8px;
    height: 8px;
    border-radius: 50%;
    background: var(--accent3);
    margin-right: 6px;
    animation: pulse 2s infinite;
  }
  @keyframes pulse {
    0%, 100% { opacity: 1; }
    50% { opacity: 0.4; }
  }
  .search-bar {
    flex: 1;
    min-width: 250px;
    max-width: 500px;
    margin-left: auto;
  }
  .search-bar input {
    width: 100%;
    padding: 10px 16px;
    border-radius: 8px;
    border: 1px solid var(--border);
    background: var(--search-bg);
    color: var(--text);
    font-size: 14px;
    outline: none;
    transition: border-color 0.2s;
  }
  .search-bar input:focus {
    border-color: var(--accent);
  }
  .search-bar input::placeholder {
    color: var(--text-dim);
  }
  .container {
    padding: 24px 32px;
    max-width: 1400px;
    margin: 0 auto;
  }
  .project-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(380px, 1fr));
    gap: 16px;
  }
  .project-card {
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 12px;
    overflow: hidden;
    transition: border-color 0.2s, transform 0.15s;
    cursor: pointer;
  }
  .project-card:hover {
    border-color: var(--accent);
    transform: translateY(-2px);
  }
  .project-card.expanded {
    grid-column: 1 / -1;
  }
  .project-header {
    padding: 16px 20px;
    display: flex;
    justify-content: space-between;
    align-items: center;
  }
  .project-name {
    font-size: 16px;
    font-weight: 600;
    color: var(--accent2);
    font-family: 'SF Mono', 'Fira Code', monospace;
  }
  .session-count {
    background: var(--surface2);
    color: var(--text-dim);
    padding: 4px 10px;
    border-radius: 12px;
    font-size: 12px;
    white-space: nowrap;
  }
  .project-sessions {
    display: none;
    border-top: 1px solid var(--border);
  }
  .project-card.expanded .project-sessions {
    display: block;
  }
  .session-item {
    padding: 14px 20px;
    border-bottom: 1px solid var(--border);
    transition: background 0.15s;
  }
  .session-item:last-child {
    border-bottom: none;
  }
  .session-item:hover {
    background: var(--surface2);
  }
  .session-meta {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 6px;
  }
  .session-date {
    font-size: 12px;
    color: var(--accent3);
    font-family: 'SF Mono', 'Fira Code', monospace;
  }
  .session-msgs {
    font-size: 11px;
    color: var(--text-dim);
  }
  .session-preview {
    font-size: 13px;
    color: var(--text-dim);
    line-height: 1.5;
    overflow: hidden;
    display: -webkit-box;
    -webkit-line-clamp: 2;
    -webkit-box-orient: vertical;
  }
  .session-all-messages {
    display: none;
    margin-top: 10px;
    padding: 10px 14px;
    background: var(--bg);
    border-radius: 8px;
    max-height: 300px;
    overflow-y: auto;
  }
  .session-item.show-messages .session-all-messages {
    display: block;
  }
  .session-all-messages .msg {
    padding: 6px 0;
    border-bottom: 1px solid var(--border);
    font-size: 12px;
    color: var(--text);
    line-height: 1.4;
  }
  .session-all-messages .msg:last-child {
    border-bottom: none;
  }
  .no-results {
    text-align: center;
    padding: 60px 20px;
    color: var(--text-dim);
    font-size: 16px;
  }
  .highlight {
    background: rgba(212, 165, 116, 0.3);
    border-radius: 2px;
    padding: 0 1px;
  }
  .memory-badge {
    display: inline-block;
    background: rgba(139, 196, 160, 0.2);
    color: var(--accent3);
    padding: 2px 8px;
    border-radius: 4px;
    font-size: 11px;
    margin-left: 8px;
    cursor: pointer;
  }
  .memory-section {
    display: none;
    border-top: 1px solid var(--border);
  }
  .project-card.show-memory .memory-section {
    display: block;
  }
  .memory-file {
    padding: 14px 20px;
    border-bottom: 1px solid var(--border);
  }
  .memory-file:last-child {
    border-bottom: none;
  }
  .memory-file-name {
    font-size: 13px;
    font-weight: 600;
    color: var(--accent3);
    font-family: 'SF Mono', 'Fira Code', monospace;
    margin-bottom: 8px;
  }
  .memory-file-content {
    font-size: 12px;
    color: var(--text-dim);
    line-height: 1.6;
    white-space: pre-wrap;
    background: var(--bg);
    padding: 12px 14px;
    border-radius: 8px;
    max-height: 400px;
    overflow-y: auto;
    font-family: 'SF Mono', 'Fira Code', monospace;
  }
  .tab-bar {
    display: flex;
    border-top: 1px solid var(--border);
    background: var(--surface2);
  }
  .tab-btn {
    flex: 1;
    padding: 8px 16px;
    font-size: 12px;
    color: var(--text-dim);
    background: none;
    border: none;
    cursor: pointer;
    text-align: center;
    transition: color 0.15s, background 0.15s;
    border-bottom: 2px solid transparent;
  }
  .tab-btn:hover {
    color: var(--text);
    background: var(--surface);
  }
  .tab-btn.active {
    color: var(--accent);
    border-bottom-color: var(--accent);
  }
  .claude-md-badge {
    display: inline-block;
    background: rgba(124, 157, 212, 0.2);
    color: var(--accent2);
    padding: 2px 8px;
    border-radius: 4px;
    font-size: 11px;
    margin-left: 8px;
  }
  .claude-md-section {
    display: none;
    border-top: 1px solid var(--border);
  }
  .project-card.show-claude-md .claude-md-section {
    display: block;
  }
  .claude-md-content {
    font-size: 12px;
    color: var(--text-dim);
    line-height: 1.6;
    white-space: pre-wrap;
    background: var(--bg);
    padding: 14px 20px;
    max-height: 500px;
    overflow-y: auto;
    font-family: 'SF Mono', 'Fira Code', monospace;
  }
</style>
</head>
<body>

<div class="header">
  <h1><span class="live-dot"></span>Claude Code Dashboard</h1>
  <span class="stats" id="stats"></span>
  <div class="search-bar">
    <input type="text" id="search" placeholder="Search projects, sessions, memory, CLAUDE.md..." autofocus>
  </div>
</div>

<div class="container">
  <div class="project-grid" id="grid"></div>
  <div class="no-results" id="no-results" style="display:none">No matching projects or sessions found.</div>
</div>

<script>
let DATA = [];
let currentVersion = 0;

const grid = document.getElementById('grid');
const searchInput = document.getElementById('search');
const statsEl = document.getElementById('stats');
const noResults = document.getElementById('no-results');

function escapeHtml(s) {
  const d = document.createElement('div');
  d.textContent = s;
  return d.innerHTML;
}

function highlightText(text, query) {
  if (!query) return escapeHtml(text);
  const escaped = escapeHtml(text);
  const re = new RegExp('(' + query.replace(/[.*+?^${}()|[\\]\\\\]/g, '\\\\$&') + ')', 'gi');
  return escaped.replace(re, '<span class="highlight">$1</span>');
}

function render(query) {
  grid.innerHTML = '';
  let visibleCount = 0;
  const q = (query || '').toLowerCase();

  const totalSessions = DATA.reduce((s, p) => s + p.sessions.length, 0);
  statsEl.textContent = DATA.length + ' projects | ' + totalSessions + ' sessions';

  DATA.forEach((project, pi) => {
    const nameMatch = !q || project.name.toLowerCase().includes(q);
    const matchingSessions = project.sessions.filter(s => {
      if (!q) return true;
      return s.first_message.toLowerCase().includes(q)
        || s.user_messages.some(m => m.toLowerCase().includes(q))
        || s.started.toLowerCase().includes(q);
    });

    const memoryMatch = q && project.memory_files && project.memory_files.some(
      mf => mf.content.toLowerCase().includes(q) || mf.name.toLowerCase().includes(q)
    );
    const claudeMdMatch = q && project.claude_md && project.claude_md.toLowerCase().includes(q);

    if (!nameMatch && matchingSessions.length === 0 && !memoryMatch && !claudeMdMatch) return;
    visibleCount++;

    const sessionsToShow = q ? matchingSessions : project.sessions;
    const hasMemory = project.memory_files && project.memory_files.length > 0;
    const hasClaudeMd = !!project.claude_md;
    const hasTabs = hasMemory || hasClaudeMd;

    const card = document.createElement('div');
    card.className = 'project-card';
    card.innerHTML = `
      <div class="project-header">
        <span class="project-name">${highlightText(project.name, q)}</span>
        <span>
          ${hasClaudeMd ? '<span class="claude-md-badge">CLAUDE.md</span>' : ''}
          ${hasMemory ? '<span class="memory-badge">' + project.memory_files.length + ' memory</span>' : ''}
          <span class="session-count">${sessionsToShow.length} session${sessionsToShow.length !== 1 ? 's' : ''}</span>
        </span>
      </div>
      ${hasTabs ? `<div class="tab-bar">
        <button class="tab-btn active" data-tab="sessions">Sessions</button>
        ${hasMemory ? '<button class="tab-btn" data-tab="memory">Memory</button>' : ''}
        ${hasClaudeMd ? '<button class="tab-btn" data-tab="claude-md">CLAUDE.md</button>' : ''}
      </div>` : ''}
      <div class="project-sessions">
        ${sessionsToShow.map((s, si) => `
          <div class="session-item" data-si="${si}">
            <div class="session-meta">
              <span class="session-date">${escapeHtml(s.started)}</span>
              <span class="session-msgs">${s.message_count} message${s.message_count !== 1 ? 's' : ''}</span>
            </div>
            <div class="session-preview">${highlightText(s.first_message, q)}</div>
            <div class="session-all-messages">
              ${s.user_messages.map(m => `<div class="msg">${highlightText(m, q)}</div>`).join('')}
            </div>
          </div>
        `).join('')}
      </div>
      ${hasMemory ? `<div class="memory-section">
        ${project.memory_files.map(mf => `
          <div class="memory-file">
            <div class="memory-file-name">${highlightText(mf.name, q)}</div>
            <div class="memory-file-content">${highlightText(mf.content, q)}</div>
          </div>
        `).join('')}
      </div>` : ''}
      ${hasClaudeMd ? `<div class="claude-md-section">
        <div class="claude-md-content">${highlightText(project.claude_md, q)}</div>
      </div>` : ''}
    `;

    card.querySelector('.project-header').addEventListener('click', () => {
      card.classList.toggle('expanded');
    });

    card.querySelectorAll('.tab-btn').forEach(btn => {
      btn.addEventListener('click', (e) => {
        e.stopPropagation();
        const tab = btn.dataset.tab;
        card.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
        card.classList.remove('show-memory', 'show-claude-md');
        const sessionsDiv = card.querySelector('.project-sessions');
        if (tab === 'memory') {
          card.classList.add('show-memory');
          sessionsDiv.style.display = 'none';
        } else if (tab === 'claude-md') {
          card.classList.add('show-claude-md');
          sessionsDiv.style.display = 'none';
        } else {
          sessionsDiv.style.display = 'block';
        }
      });
    });

    card.querySelectorAll('.session-item').forEach(el => {
      el.addEventListener('click', (e) => {
        e.stopPropagation();
        el.classList.toggle('show-messages');
      });
    });

    if (q) {
      card.classList.add('expanded');
      const sessionsDiv = card.querySelector('.project-sessions');
      if (matchingSessions.length === 0 && (memoryMatch || claudeMdMatch)) {
        const bestTab = memoryMatch ? 'memory' : 'claude-md';
        if (bestTab === 'memory') card.classList.add('show-memory');
        else card.classList.add('show-claude-md');
        if (sessionsDiv) sessionsDiv.style.display = 'none';
        card.querySelectorAll('.tab-btn').forEach(b => {
          b.classList.toggle('active', b.dataset.tab === bestTab);
        });
      }
    }

    grid.appendChild(card);
  });

  noResults.style.display = visibleCount === 0 ? 'block' : 'none';
}

searchInput.addEventListener('input', (e) => {
  render(e.target.value);
});

// Poll for updates
async function checkForUpdates() {
  try {
    const resp = await fetch('/api/data?v=' + currentVersion);
    const result = await resp.json();
    if (result.version !== currentVersion) {
      currentVersion = result.version;
      DATA = result.data;
      render(searchInput.value);
    }
  } catch (e) {}
  setTimeout(checkForUpdates, 3000);
}

// Initial load
fetch('/api/data').then(r => r.json()).then(result => {
  currentVersion = result.version;
  DATA = result.data;
  render('');
  setTimeout(checkForUpdates, 3000);
});
</script>
</body>
</html>"""


# --- HTTP Server ---

class DashboardHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/" or self.path == "/index.html":
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(get_html().encode())
        elif self.path.startswith("/api/data"):
            data_json, version = get_state().get()
            response = json.dumps({"version": version, "data": json.loads(data_json)})
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(response.encode())
        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, format, *args):
        pass  # suppress request logs


def main():
    port = DEFAULT_PORT
    if len(sys.argv) > 1:
        for i, arg in enumerate(sys.argv[1:]):
            if arg == "--port" and i + 2 < len(sys.argv):
                port = int(sys.argv[i + 2])
            elif arg.isdigit():
                port = int(arg)

    # Start file watcher
    t = threading.Thread(target=watcher_thread, daemon=True)
    t.start()

    server = HTTPServer(("127.0.0.1", port), DashboardHandler)
    print(f"Claude Code Dashboard running at http://localhost:{port}")
    print(f"Watching {PROJECTS_DIR} for changes (every {POLL_INTERVAL}s)")
    print("Press Ctrl+C to stop\n")

    try:
        import webbrowser
        webbrowser.open(f"http://localhost:{port}")
    except Exception:
        pass

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped.")
        server.server_close()


if __name__ == "__main__":
    main()
