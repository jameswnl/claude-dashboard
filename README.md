# Claude Code Dashboard

A visual dashboard for browsing Claude Code projects, sessions, memory files, and CLAUDE.md configs.

Scans `~/.claude/projects/` and presents everything in a searchable web UI.

## Features

- Browse all projects with session counts
- Expand projects to see session history and first messages
- View memory files and CLAUDE.md per project
- Full-text search across project names, session messages, memory, and CLAUDE.md
- Auto-highlights search matches
- Live auto-refresh when files change

## Setup

Requires [uv](https://docs.astral.sh/uv/) and Python 3.10+.

```bash
uv sync
```

## Usage

```bash
uv run claude-dashboard
```

Opens at http://localhost:8420. Custom port:

```bash
uv run claude-dashboard --port 9000
```

## Tests

```bash
uv run pytest
```

## How it works

- Polls `~/.claude/projects/` every 3 seconds for file changes
- Browser auto-updates via polling `/api/data`
- No external dependencies beyond Python stdlib
