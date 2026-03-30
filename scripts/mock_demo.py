#!/usr/bin/env python3
"""Create mock project data and launch the dashboard for screenshots."""

import json
import os
import sys
import tempfile
import uuid
from datetime import datetime, timedelta
from pathlib import Path


def make_session(project_dir, messages, hours_ago=0):
    """Create a mock session .jsonl file."""
    session_id = str(uuid.uuid4())[:36]
    ts = (datetime.now() - timedelta(hours=hours_ago)).isoformat() + "Z"
    jsonl_path = project_dir / f"{session_id}.jsonl"
    lines = []
    for i, msg in enumerate(messages):
        t = (datetime.now() - timedelta(hours=hours_ago) + timedelta(minutes=i)).isoformat() + "Z"
        lines.append(json.dumps({
            "type": "user",
            "message": {"role": "user", "content": msg},
            "timestamp": t,
        }))
        lines.append(json.dumps({
            "type": "assistant",
            "message": {"role": "assistant", "content": "Done."},
            "timestamp": t,
        }))
    jsonl_path.write_text("\n".join(lines) + "\n")


def make_memory(project_dir, name, content):
    """Create a memory file."""
    mem_dir = project_dir / "memory"
    mem_dir.mkdir(exist_ok=True)
    (mem_dir / name).write_text(content)


def setup_mock_data(base_dir):
    """Create realistic-looking mock projects."""

    # --- Project 1: webapp ---
    p1 = base_dir / "-Users-demo-projects-webapp"
    p1.mkdir()
    make_session(p1, [
        "Add dark mode toggle to the settings page",
        "The toggle should persist across page reloads using localStorage",
        "Also update the header component to respect the theme",
    ], hours_ago=2)
    make_session(p1, [
        "Fix the login form validation — email regex is too strict",
        "Add a proper error message below the input field",
    ], hours_ago=24)
    make_session(p1, [
        "Set up ESLint and Prettier with the team's config",
    ], hours_ago=48)
    make_session(p1, [
        "Refactor the API client to use axios interceptors for auth",
        "Add automatic token refresh on 401 responses",
        "Write tests for the interceptor logic",
    ], hours_ago=72)
    make_session(p1, [
        "Create a reusable Modal component with animations",
    ], hours_ago=120)
    make_memory(p1, "MEMORY.md", """# Webapp Project

## Stack
- React 18 + TypeScript
- Tailwind CSS for styling
- Vite for bundling
- Vitest + Testing Library for tests

## Conventions
- Use functional components with hooks
- Prefer named exports
- Tests co-located in __tests__ directories
- API calls go through src/api/ client module

## Key Decisions
- Chose Zustand over Redux for state management (simpler API)
- Using React Router v6 with lazy loading
""")

    # --- Project 2: api-service ---
    p2 = base_dir / "-Users-demo-projects-api-service"
    p2.mkdir()
    make_session(p2, [
        "Add rate limiting middleware using Redis",
        "Configure 100 req/min per API key",
        "Add rate limit headers to responses (X-RateLimit-*)",
    ], hours_ago=1)
    make_session(p2, [
        "Create database migration for the new orders table",
        "Add foreign key to users table",
    ], hours_ago=36)
    make_session(p2, [
        "Fix N+1 query in the /api/products endpoint",
        "Use eager loading with SQLAlchemy joinedload",
    ], hours_ago=96)
    make_memory(p2, "MEMORY.md", """# API Service

## Stack
- Python 3.12, FastAPI, SQLAlchemy 2.0
- PostgreSQL + Redis
- Alembic for migrations

## Patterns
- Repository pattern for data access
- Pydantic models for request/response validation
- Dependency injection via FastAPI Depends()
""")

    # --- Project 3: ml-pipeline ---
    p3 = base_dir / "-Users-demo-research-ml-pipeline"
    p3.mkdir()
    make_session(p3, [
        "Implement a data preprocessing pipeline for the text classification model",
        "Add tokenization, stopword removal, and TF-IDF vectorization steps",
    ], hours_ago=5)
    make_session(p3, [
        "Add cross-validation to the training script",
        "Report precision, recall, and F1 per fold",
    ], hours_ago=168)
    make_memory(p3, "MEMORY.md", """# ML Pipeline

## Overview
Text classification pipeline for support ticket routing.

## Models
- Baseline: LogisticRegression with TF-IDF (F1: 0.82)
- Current: Fine-tuned DistilBERT (F1: 0.91)

## Data
- Training set: 50k labeled tickets
- Validation: 10k tickets
- Test: 5k tickets (held out)
""")

    # --- Project 4: infra (small) ---
    p4 = base_dir / "-Users-demo-infra-terraform"
    p4.mkdir()
    make_session(p4, [
        "Add a Terraform module for the new staging environment",
        "Mirror prod but with smaller instance sizes",
    ], hours_ago=200)
    make_memory(p4, "MEMORY.md", """# Infrastructure

## Cloud: AWS (us-east-1)
## IaC: Terraform with remote S3 backend
## Environments: dev, staging, prod
""")

    # --- Project 5: docs-site ---
    p5 = base_dir / "-Users-demo-projects-docs-site"
    p5.mkdir()
    make_session(p5, [
        "Add a search feature using Algolia DocSearch",
        "Index all markdown pages on build",
    ], hours_ago=12)
    make_session(p5, [
        "Fix broken links in the API reference section",
    ], hours_ago=50)

    # --- Project 6: mobile-app ---
    p6 = base_dir / "-Users-demo-projects-mobile-app"
    p6.mkdir()
    make_session(p6, [
        "Set up React Native project with Expo",
        "Configure navigation with React Navigation v6",
        "Add bottom tab navigator with Home, Search, Profile tabs",
    ], hours_ago=3)
    make_session(p6, [
        "Implement pull-to-refresh on the feed screen",
    ], hours_ago=30)
    make_session(p6, [
        "Add push notification support with Expo Notifications",
        "Handle notification tap to navigate to the relevant screen",
    ], hours_ago=80)

    print(f"Mock data created in {base_dir}")
    return base_dir


def setup_mock_claude_dir(claude_dir):
    """Create mock ~/.claude with skills and MCP config."""
    claude_dir.mkdir(exist_ok=True)

    # User-level skills/commands
    commands_dir = claude_dir / "commands"
    commands_dir.mkdir(exist_ok=True)

    (commands_dir / "commit.md").write_text(
        "Review staged changes and create a well-formatted git commit.\n"
        "Include a concise summary and relevant details in the commit message.\n"
    )
    (commands_dir / "review.md").write_text(
        "Review the current PR for code quality, bugs, and style issues.\n"
        "Suggest improvements and flag any potential problems.\n"
    )
    (commands_dir / "test.md").write_text(
        "Run the project's test suite and report results.\n"
        "If tests fail, analyze the failures and suggest fixes.\n"
    )

    # Plugin skills
    plugins_dir = claude_dir / "plugins" / "marketplaces" / "official" / "plugins"
    plugin1_dir = plugins_dir / "code-review-helper"
    (plugin1_dir / "commands").mkdir(parents=True, exist_ok=True)
    (plugin1_dir / "README.md").write_text(
        "# Code Review Helper\n\n"
        "Automated code review with best practices.\n\n"
        "Source: https://github.com/example/code-review-helper\n"
    )
    (plugin1_dir / "commands" / "lint-fix.md").write_text(
        "Run linters and automatically fix issues where possible.\n"
        "Report remaining issues that need manual attention.\n"
    )
    (plugin1_dir / "commands" / "security-scan.md").write_text(
        "Scan the codebase for common security vulnerabilities.\n"
        "Check for OWASP Top 10 issues and dependency vulnerabilities.\n"
    )

    plugin2_dir = plugins_dir / "doc-generator"
    (plugin2_dir / "commands").mkdir(parents=True, exist_ok=True)
    (plugin2_dir / "README.md").write_text(
        "# Doc Generator\n\n"
        "Generate documentation from code.\n\n"
        "Source: https://github.com/example/doc-generator\n"
    )
    (plugin2_dir / "commands" / "generate-api-docs.md").write_text(
        "Generate API documentation from route handlers and schemas.\n"
        "Output in OpenAPI/Swagger format.\n"
    )

    # User-level MCP config (~/.claude.json)
    claude_json = claude_dir.parent / ".claude.json"
    claude_json.write_text(json.dumps({
        "mcpServers": {
            "github": {
                "type": "stdio",
                "command": "npx",
                "args": ["-y", "@modelcontextprotocol/server-github"],
                "env": {
                    "GITHUB_TOKEN": "ghp_FAKE_TOKEN_FOR_DEMO"
                }
            },
            "slack": {
                "type": "sse",
                "url": "http://localhost:3100/sse",
                "headers": {
                    "Authorization": "Bearer xoxb-FAKE-DEMO-TOKEN",
                    "Content-Type": "application/json"
                }
            },
            "filesystem": {
                "type": "stdio",
                "command": "npx",
                "args": ["-y", "@modelcontextprotocol/server-filesystem", "/Users/demo/projects"]
            },
            "jira": {
                "type": "sse",
                "url": "https://mcp.atlassian.com/v1/sse",
                "headers": {
                    "Authorization": "Bearer FAKE_JWT_FOR_DEMO",
                    "x-api-key": "ak_FAKE_DEMO_KEY"
                }
            }
        }
    }, indent=2))


def main():
    tmpdir = Path(tempfile.mkdtemp(prefix="claude_dashboard_demo_"))
    mock_dir = setup_mock_data(tmpdir)

    # Create mock ~/.claude dir
    mock_claude_dir = tmpdir / ".claude"
    setup_mock_claude_dir(mock_claude_dir)

    print(f"\nMock projects directory: {mock_dir}")
    print(f"\nStarting dashboard...\n")

    os.environ["CLAUDE_PROJECTS_DIR"] = str(mock_dir)

    # Import and run the server
    sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

    # Monkey-patch CLAUDE_DIR and Path.home() to use our mock
    import claude_dashboard.data as data_mod
    data_mod.CLAUDE_DIR = mock_claude_dir
    data_mod.PROJECTS_DIR = mock_dir

    # Patch Path.home() so ~/.claude.json resolves to our mock
    _real_home = Path.home
    Path.home = staticmethod(lambda: tmpdir)

    # Pass a different port to avoid conflicts
    port = 8421
    if len(sys.argv) > 1:
        port = int(sys.argv[1])
    sys.argv = ["claude-dashboard", "--port", str(port)]
    # Patch server.main to not open browser and to write token to file
    import claude_dashboard.server as srv_mod
    srv_mod.state = None  # reset state so it picks up our mock CLAUDE_DIR

    original_main = srv_mod.main

    def patched_main():
        import webbrowser
        real_open = webbrowser.open
        def capture_open(url):
            Path("/tmp/mock_dashboard_token.txt").write_text(url + "\n")
            real_open(url)
        webbrowser.open = capture_open
        original_main()

    patched_main()


if __name__ == "__main__":
    main()
