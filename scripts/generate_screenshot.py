#!/usr/bin/env python3
"""Generate a dashboard screenshot with demo data (no real user data)."""

import json
import subprocess
import sys
import tempfile
import threading
import time
from http.server import HTTPServer, BaseHTTPRequestHandler
from pathlib import Path

DEMO_DATA = [
    {
        "name": "~/projects/web-app",
        "dirname": "-home-user-projects-web-app",
        "has_memory": True,
        "claude_md": "# Web App\n\n- Use TypeScript for all new code\n- Run `npm test` before committing\n- Prefer functional components in React",
        "memory_files": [
            {"name": "MEMORY.md", "content": "# Web App Project\n\n## Stack\n- React 19 + TypeScript\n- Vite for bundling\n- Tailwind CSS\n\n## Key decisions\n- Using server components for data fetching\n- Auth via NextAuth.js"}
        ],
        "sessions": [
            {"id": "a1", "first_message": "Add dark mode toggle to the settings page", "user_messages": ["Add dark mode toggle to the settings page", "Make it persist in localStorage", "Also update the navbar component"], "started": "2026-03-24 14:30", "last_activity": "2026-03-24 15:10", "message_count": 12},
            {"id": "a2", "first_message": "Fix the login redirect bug on Safari", "user_messages": ["Fix the login redirect bug on Safari", "Can you check the auth middleware too?"], "started": "2026-03-23 09:15", "last_activity": "2026-03-23 10:00", "message_count": 8},
            {"id": "a3", "first_message": "Refactor the API client to use fetch instead of axios", "user_messages": ["Refactor the API client to use fetch instead of axios"], "started": "2026-03-22 16:45", "last_activity": "2026-03-22 17:30", "message_count": 6},
            {"id": "a4", "first_message": "Set up CI pipeline with GitHub Actions", "user_messages": ["Set up CI pipeline with GitHub Actions", "Add test coverage reporting"], "started": "2026-03-20 11:00", "last_activity": "2026-03-20 12:15", "message_count": 15},
        ],
    },
    {
        "name": "~/projects/api-server",
        "dirname": "-home-user-projects-api-server",
        "has_memory": True,
        "claude_md": None,
        "memory_files": [
            {"name": "MEMORY.md", "content": "# API Server\n\n## Architecture\n- FastAPI + SQLAlchemy\n- PostgreSQL database\n- Redis for caching\n\n## Conventions\n- All endpoints return JSON\n- Use Pydantic models for validation"}
        ],
        "sessions": [
            {"id": "b1", "first_message": "Add rate limiting middleware", "user_messages": ["Add rate limiting middleware", "Use Redis for the token bucket"], "started": "2026-03-24 10:00", "last_activity": "2026-03-24 11:30", "message_count": 10},
            {"id": "b2", "first_message": "Write migration for the new users table schema", "user_messages": ["Write migration for the new users table schema"], "started": "2026-03-21 14:00", "last_activity": "2026-03-21 14:45", "message_count": 5},
            {"id": "b3", "first_message": "Debug the N+1 query issue on /api/orders", "user_messages": ["Debug the N+1 query issue on /api/orders", "Add eager loading for the relationships"], "started": "2026-03-19 09:30", "last_activity": "2026-03-19 10:45", "message_count": 9},
        ],
    },
    {
        "name": "~/projects/ml-pipeline",
        "dirname": "-home-user-projects-ml-pipeline",
        "has_memory": False,
        "claude_md": "# ML Pipeline\n\n- Python 3.11+\n- Use PyTorch for model training\n- Store artifacts in S3",
        "memory_files": [],
        "sessions": [
            {"id": "c1", "first_message": "Optimize the data preprocessing step for larger datasets", "user_messages": ["Optimize the data preprocessing step for larger datasets"], "started": "2026-03-22 13:00", "last_activity": "2026-03-22 14:30", "message_count": 7},
            {"id": "c2", "first_message": "Add model versioning with MLflow", "user_messages": ["Add model versioning with MLflow", "Set up the tracking server config"], "started": "2026-03-18 10:00", "last_activity": "2026-03-18 11:45", "message_count": 11},
        ],
    },
    {
        "name": "~/dotfiles",
        "dirname": "-home-user-dotfiles",
        "has_memory": False,
        "claude_md": None,
        "memory_files": [],
        "sessions": [
            {"id": "d1", "first_message": "Update my zsh config to use starship prompt", "user_messages": ["Update my zsh config to use starship prompt"], "started": "2026-03-15 20:00", "last_activity": "2026-03-15 20:30", "message_count": 4},
        ],
    },
    {
        "name": "~/projects/docs",
        "dirname": "-home-user-projects-docs",
        "has_memory": True,
        "claude_md": None,
        "memory_files": [
            {"name": "MEMORY.md", "content": "# Documentation Site\n\n- Built with MkDocs + Material theme\n- Deploy to GitHub Pages"}
        ],
        "sessions": [
            {"id": "e1", "first_message": "Add search functionality to the docs site", "user_messages": ["Add search functionality to the docs site"], "started": "2026-03-17 15:00", "last_activity": "2026-03-17 15:45", "message_count": 5},
        ],
    },
    {
        "name": "~/projects/mobile-app",
        "dirname": "-home-user-projects-mobile-app",
        "has_memory": False,
        "claude_md": None,
        "memory_files": [],
        "sessions": [
            {"id": "f1", "first_message": "Set up React Native navigation with expo-router", "user_messages": ["Set up React Native navigation with expo-router"], "started": "2026-03-16 11:00", "last_activity": "2026-03-16 12:00", "message_count": 8},
        ],
    },
]


# Reuse get_html from the main server module
from claude_dashboard.server import get_html


class DemoHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/" or self.path == "/index.html":
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(get_html().encode())
        elif self.path.startswith("/api/data"):
            response = json.dumps({"version": 1, "data": DEMO_DATA})
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(response.encode())
        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, format, *args):
        pass


def main():
    port = 8421
    server = HTTPServer(("127.0.0.1", port), DemoHandler)
    t = threading.Thread(target=server.serve_forever, daemon=True)
    t.start()
    print(f"Demo server running at http://localhost:{port}")

    screenshot_path = Path(__file__).parent.parent / "screenshot.png"

    # Try to take screenshot with npx playwright
    try:
        script = f"""
const {{ chromium }} = require('playwright');
(async () => {{
  const browser = await chromium.launch();
  const page = await browser.newPage({{ viewport: {{ width: 1280, height: 800 }} }});
  await page.goto('http://localhost:{port}');
  await page.waitForSelector('.project-card');
  await page.waitForTimeout(500);
  // Expand first two projects
  const headers = await page.$$('.project-header');
  if (headers.length > 0) await headers[0].click();
  if (headers.length > 1) await headers[1].click();
  await page.waitForTimeout(300);
  await page.screenshot({{ path: '{screenshot_path}', fullPage: false }});
  await browser.close();
}})();
"""
        with tempfile.NamedTemporaryFile(suffix=".js", mode="w", delete=False) as f:
            f.write(script)
            f.flush()
            result = subprocess.run(
                ["npx", "--yes", "playwright", "test", "--browser=chromium"],
                capture_output=True, text=True, timeout=30,
                cwd=str(Path(__file__).parent.parent),
            )
            # If that doesn't work, try direct node execution
            if not screenshot_path.exists():
                subprocess.run(
                    ["node", "-e", script],
                    capture_output=True, text=True, timeout=30,
                )
    except Exception as e:
        print(f"Playwright failed: {e}")

    if not screenshot_path.exists():
        # Fallback: try macOS screencapture with open
        print(f"\nAutomatic screenshot failed.")
        print(f"Please take a manual screenshot:")
        print(f"  1. Open http://localhost:{port}")
        print(f"  2. Expand a couple of project cards")
        print(f"  3. Save screenshot as: {screenshot_path}")
        print(f"\nPress Enter when done (or Ctrl+C to skip)...")
        import webbrowser
        webbrowser.open(f"http://localhost:{port}")
        try:
            input()
        except (KeyboardInterrupt, EOFError):
            pass
    else:
        print(f"Screenshot saved to: {screenshot_path}")

    server.shutdown()


if __name__ == "__main__":
    main()
