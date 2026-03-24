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
import sys
import time
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from pathlib import Path
from datetime import datetime

from . import data as _data
from .data import collect_data, get_dir_fingerprint, PROJECTS_DIR
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

    def do_POST(self):
        if self.path == "/api/refresh":
            get_state().refresh()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(b'{"ok": true}')
        elif self.path == "/api/resume":
            content_length = int(self.headers.get("Content-Length", 0))
            body = json.loads(self.rfile.read(content_length))
            session_id = body.get("session_id", "")
            dirname = body.get("dirname", "")
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
    print(f"Claude Code Dashboard running at http://localhost:{port}")
    print(f"Watching {_data.PROJECTS_DIR} for changes (every {POLL_INTERVAL}s)")
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
