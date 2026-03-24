"""HTML/CSS/JS template for the dashboard UI."""


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
  .resume-btn {
    padding: 4px 12px;
    border-radius: 6px;
    border: 1px solid var(--accent2);
    background: transparent;
    color: var(--accent2);
    font-size: 11px;
    cursor: pointer;
    transition: background 0.15s, color 0.15s;
    white-space: nowrap;
  }
  .resume-btn:hover {
    background: var(--accent2);
    color: var(--bg);
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
  .refresh-btn {
    padding: 8px 16px;
    border-radius: 8px;
    border: 1px solid var(--border);
    background: var(--surface2);
    color: var(--text-dim);
    font-size: 13px;
    cursor: pointer;
    transition: background 0.15s, color 0.15s, border-color 0.15s;
    white-space: nowrap;
  }
  .refresh-btn:hover {
    background: var(--surface);
    color: var(--text);
    border-color: var(--accent);
  }
  .refresh-btn.loading {
    opacity: 0.5;
    pointer-events: none;
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
  <button class="refresh-btn" id="refresh" title="Refresh data">Refresh</button>
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
              <button class="resume-btn" data-session-id="${escapeHtml(s.id)}" data-dirname="${escapeHtml(project.dirname)}">Resume</button>
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

    card.querySelectorAll('.resume-btn').forEach(btn => {
      btn.addEventListener('click', async (e) => {
        e.stopPropagation();
        const sessionId = btn.dataset.sessionId;
        const dirname = btn.dataset.dirname;
        btn.textContent = 'Opening...';
        try {
          const resp = await fetch('/api/resume', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({session_id: sessionId, dirname: dirname})
          });
          const result = await resp.json();
          if (!result.ok) alert('Failed to open terminal: ' + (result.error || 'unknown error'));
        } catch (err) {
          alert('Failed to resume session: ' + err.message);
        }
        btn.textContent = 'Resume';
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

async function fetchData() {
  const resp = await fetch('/api/data');
  const result = await resp.json();
  if (result.version !== currentVersion) {
    currentVersion = result.version;
    DATA = result.data;
    render(searchInput.value);
  }
}

// Manual refresh
const refreshBtn = document.getElementById('refresh');
refreshBtn.addEventListener('click', async () => {
  refreshBtn.classList.add('loading');
  refreshBtn.textContent = 'Refreshing...';
  try {
    await fetch('/api/refresh', { method: 'POST' });
    await fetchData();
  } catch (e) {}
  refreshBtn.classList.remove('loading');
  refreshBtn.textContent = 'Refresh';
});

// Initial load
fetchData();
</script>
</body>
</html>"""
