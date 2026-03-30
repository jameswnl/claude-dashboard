# Scripts

## mock_demo.py

Launches the dashboard with fake project data for capturing screenshots. All real data sources (`~/.claude/`, `~/.claude.json`) are monkey-patched so nothing personal is exposed.

### Usage

```bash
uv run python scripts/mock_demo.py         # default port 8421
uv run python scripts/mock_demo.py 8500    # custom port
```

Opens your browser automatically. The token URL is also saved to `/tmp/mock_dashboard_token.txt`.

**Note:** If you see `{"error": "unauthorized: invalid token"}`, clear your browser's cookies for `localhost` (or use an incognito window). A stale auth cookie from a previous session can override the new token.

### What it creates

| Data | Details |
|------|---------|
| **Projects** | 6 fake projects (webapp, api-service, ml-pipeline, infra, docs-site, mobile-app) |
| **Sessions** | 1–5 sessions per project with realistic messages |
| **Memory files** | MEMORY.md with stack info and conventions |
| **Skills** | 3 user commands, 2 plugins with multiple skills |
| **MCP Servers** | 4 user-level servers (github, slack, filesystem, jira) with masked secrets |

All data is created in a temp directory and cleaned up on exit.
