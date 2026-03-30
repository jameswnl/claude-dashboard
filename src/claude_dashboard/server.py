#!/usr/bin/env python3
"""Live dashboard server for Claude Code projects.

Serves the dashboard on http://localhost:8420 and auto-refreshes
when files change in ~/.claude/projects/.

Usage:
    claude-dashboard
    claude-dashboard --port 9000
    claude-dashboard --projects-dir /path/to/projects

Set CLAUDE_PROJECTS_DIR env var to override the default projects directory.
"""

import json
import secrets
import sys
import time
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from pathlib import Path
from datetime import datetime

from . import data as _data
from .data import collect_data, collect_all_skills, collect_mcp_servers, get_dir_fingerprint, PROJECTS_DIR
from .data import extract_memory_files, extract_sessions
from .ui import get_html
from .utils import (
    dirname_to_path,
    find_claude_md,
    format_date,
    open_terminal_with_session,
    project_display_name,
    read_claude_md,
)

DEFAULT_PORT = 8420
POLL_INTERVAL = 600  # seconds (10 minutes)
ALLOWED_HOSTS = {"localhost", "127.0.0.1"}

# Per-launch auth token — generated once at import time
AUTH_TOKEN = secrets.token_urlsafe(32)


# --- Shared state ---

class DashboardState:
    def __init__(self):
        self.lock = threading.Lock()
        self.data_json = "[]"
        self.skills_json = "{}"
        self.mcp_json = "{}"
        self.version = 0
        self.refresh()

    def refresh(self):
        data = collect_data()
        skills = collect_all_skills()
        mcp = collect_mcp_servers()
        with self.lock:
            self.data_json = json.dumps(data)
            self.skills_json = json.dumps(skills)
            self.mcp_json = json.dumps(mcp)
            self.version += 1

    def get(self):
        with self.lock:
            return self.data_json, self.skills_json, self.mcp_json, self.version


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
                print(f"[{datetime.now().strftime('%H:%M:%S')}] Data refreshed (v{get_state().get()[-1]})")
        except Exception as e:
            print(f"Watcher error: {e}")


# --- HTTP Server ---

class DashboardHandler(BaseHTTPRequestHandler):
    def _check_host(self):
        """Reject requests with unexpected Host headers (DNS rebinding protection)."""
        host = self.headers.get("Host", "")
        hostname = host.split(":")[0]
        if hostname not in ALLOWED_HOSTS:
            self.send_response(403)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(b'{"error": "forbidden: invalid host"}')
            return False
        return True

    def _get_token(self):
        """Extract auth token from Authorization header, query string, or cookie."""
        # Authorization header (used by JS fetch)
        auth = self.headers.get("Authorization", "")
        if auth.startswith("Bearer "):
            return auth[7:]
        # Query string: /?token=... (initial browser open) — checked before
        # cookie so a new token URL always works even with a stale cookie
        if "?" in self.path:
            for param in self.path.split("?", 1)[1].split("&"):
                if param.startswith("token="):
                    return param[6:]
        # Cookie (set after initial auth via token URL)
        cookie = self.headers.get("Cookie", "")
        for part in cookie.split(";"):
            part = part.strip()
            if part.startswith("dashboard_token="):
                return part[16:]
        return None

    def _check_auth(self):
        """Verify per-launch auth token."""
        if self._get_token() != AUTH_TOKEN:
            self.send_response(401)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(b'{"error": "unauthorized: invalid token"}')
            return False
        return True

    def _check_origin(self):
        """Validate Origin header for POST requests (CSRF protection)."""
        origin = self.headers.get("Origin", "")
        if origin:
            # Extract hostname from origin URL
            try:
                from urllib.parse import urlparse
                parsed = urlparse(origin)
                if parsed.hostname not in ALLOWED_HOSTS:
                    self.send_response(403)
                    self.send_header("Content-Type", "application/json")
                    self.end_headers()
                    self.wfile.write(b'{"error": "forbidden: invalid origin"}')
                    return False
            except Exception:
                self.send_response(403)
                self.end_headers()
                return False
        return True

    def _validate_session(self, session_id, dirname):
        """Verify session_id and dirname exist in the current dataset."""
        data_json = get_state().get()[0]
        data = json.loads(data_json)
        for project in data:
            if project.get("dirname") == dirname:
                for session in project.get("sessions", []):
                    if session.get("id") == session_id:
                        return True
        return False

    def do_GET(self):
        if not self._check_host():
            return
        base_path = self.path.split("?")[0]
        if base_path == "/" or base_path == "/index.html":
            if not self._check_auth():
                return
            # If token came via query string, set cookie and redirect to clean URL
            if "?" in self.path and "token=" in self.path:
                self.send_response(302)
                self.send_header("Location", "/")
                self.send_header("Set-Cookie", f"dashboard_token={AUTH_TOKEN}; HttpOnly; SameSite=Strict; Path=/")
                self.end_headers()
                return
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(get_html(AUTH_TOKEN).encode())
        elif self.path.startswith("/api/data"):
            if not self._check_auth():
                return
            data_json, skills_json, mcp_json, version = get_state().get()
            response = json.dumps({
                "version": version,
                "data": json.loads(data_json),
                "skills": json.loads(skills_json),
                "mcp": json.loads(mcp_json),
            })
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(response.encode())
        else:
            self.send_response(404)
            self.end_headers()

    def do_POST(self):
        if not self._check_host():
            return
        if not self._check_auth():
            return
        if not self._check_origin():
            return
        if self.path.startswith("/api/refresh"):
            get_state().refresh()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(b'{"ok": true}')
        elif self.path.startswith("/api/resume"):
            content_length = int(self.headers.get("Content-Length", 0))
            body = json.loads(self.rfile.read(content_length))
            session_id = body.get("session_id", "")
            dirname = body.get("dirname", "")
            if not self._validate_session(session_id, dirname):
                self.send_response(400)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(b'{"error": "unknown session or project"}')
                return
            result = open_terminal_with_session(session_id, dirname)
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(result).encode())
        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, format, *args):
        pass  # suppress request logs


def main():
    port = DEFAULT_PORT
    if len(sys.argv) > 1:
        args = sys.argv[1:]
        i = 0
        while i < len(args):
            if args[i] == "--port" and i + 1 < len(args):
                port = int(args[i + 1])
                i += 2
            elif args[i] == "--projects-dir" and i + 1 < len(args):
                _data.PROJECTS_DIR = Path(args[i + 1])
                i += 2
            elif args[i].isdigit():
                port = int(args[i])
                i += 1
            else:
                i += 1

    # Start file watcher
    t = threading.Thread(target=watcher_thread, daemon=True)
    t.start()

    server = HTTPServer(("127.0.0.1", port), DashboardHandler)
    dashboard_url = f"http://localhost:{port}/?token={AUTH_TOKEN}"
    print(f"Claude Code Dashboard running at {dashboard_url}")
    print(f"Watching {_data.PROJECTS_DIR} for changes (every {POLL_INTERVAL}s)")
    print("Press Ctrl+C to stop\n")

    try:
        import webbrowser
        webbrowser.open(dashboard_url)
    except Exception:
        pass

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped.")
        server.server_close()


if __name__ == "__main__":
    main()
