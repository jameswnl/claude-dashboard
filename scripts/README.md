# Scripts

## mock_demo.py

Launches the dashboard with fake project data for capturing screenshots. All real data sources (`~/.claude/`, `~/.claude.json`) are monkey-patched so nothing personal is exposed.

### Usage

```bash
uv run python scripts/mock_demo.py         # default port 8421
uv run python scripts/mock_demo.py 8500    # custom port
```

Opens your browser automatically. The token URL is also saved to `/tmp/mock_dashboard_token.txt`.

### What it creates

| Data | Details |
|------|---------|
| **Projects** | 6 fake projects (webapp, api-service, ml-pipeline, infra, docs-site, mobile-app) |
| **Sessions** | 1–5 sessions per project with realistic messages |
| **Memory files** | MEMORY.md with stack info and conventions |
| **Skills** | 3 user commands, 2 plugins with multiple skills |
| **MCP Servers** | 4 user-level servers (github, slack, filesystem, jira) with masked secrets |

All data is created in a temp directory and cleaned up on exit.

## install_menubar_app.sh

Installs the Claude Dashboard menubar app to `/Applications` on macOS. The app shows a `C>_` icon in the menu bar for starting/stopping the dashboard server and opening it in your browser.

### Usage

```bash
./scripts/install_menubar_app.sh
```

### What it does

1. Installs `claude-dashboard` with the `menubar` extra (uses `uv` if available, falls back to `pip`)
2. Creates a `.app` bundle at `/Applications/Claude Dashboard.app`
3. The app runs as a menubar-only icon (no Dock icon)

### Start at login

System Settings → General → Login Items → add "Claude Dashboard"
