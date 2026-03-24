# Claude Code Dashboard

A visual dashboard for browsing Claude Code projects, sessions, memory files, and CLAUDE.md configs.

Scans `~/.claude/projects/` and presents everything in a searchable web UI.

## Features

- Browse all projects with session counts
- Expand projects to see session history and first messages
- View memory files and CLAUDE.md per project
- Full-text search across project names, session messages, memory, and CLAUDE.md
- Auto-highlights search matches

## Usage

```bash
python3 claude-dashboard-server.py
```

Opens at http://localhost:8420. Custom port:

```bash
python3 claude-dashboard-server.py --port 9000
```

- Polls `~/.claude/projects/` every 3 seconds for changes
- Browser auto-updates without reload
- No dependencies beyond Python 3 stdlib
