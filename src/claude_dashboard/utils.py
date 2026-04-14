"""Utility functions for path resolution, date formatting, and terminal launch."""

import json
import os
import shlex
import subprocess
import tempfile
from datetime import datetime
from pathlib import Path


def dirname_to_path(dirname):
    """Convert a project dirname back to a filesystem path.

    Handles ambiguity where '-' could be a path separator or a literal hyphen
    by probing the filesystem to find the correct path.
    """
    parts = dirname.lstrip("-").split("-")
    if not parts:
        return "/"

    # Try greedy filesystem probing: at each step, try joining with hyphen
    # to match directories that contain hyphens in their names.
    path = Path("/")
    i = 0
    while i < len(parts):
        # Try longest hyphenated match first
        matched = False
        for j in range(len(parts), i, -1):
            candidate = "-".join(parts[i:j])
            if (path / candidate).exists():
                path = path / candidate
                i = j
                matched = True
                break
        if not matched:
            # No match found, just use the single part
            path = path / parts[i]
            i += 1
    return str(path)


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


def project_display_name(dirname):
    """Convert project dirname to readable path like ~/ws/jira.

    Uses dirname_to_path for accurate resolution (handles hyphenated dirs),
    then replaces home directory prefix with ~.
    """
    path = dirname_to_path(dirname)
    home = str(Path.home())
    if path == home:
        return "~"
    if path.startswith(home + "/"):
        return "~" + path[len(home):]
    return path


def format_date(iso_str):
    if not iso_str:
        return ""
    try:
        dt = datetime.fromisoformat(iso_str.replace("Z", "+00:00"))
        return dt.strftime("%Y-%m-%d %H:%M")
    except Exception:
        return iso_str[:16]


def open_terminal_with_session(session_id, dirname):
    """Open a terminal and run 'claude --resume <session_id>' in the project dir."""
    project_path = dirname_to_path(dirname)
    if Path(project_path).is_dir():
        cmd = f"cd {shlex.quote(project_path)} && claude --resume {shlex.quote(session_id)}"
    else:
        # Path may have hyphens that were ambiguously encoded; resume without cd
        cmd = f"claude --resume {shlex.quote(session_id)}"

    # Use a .command file — macOS opens these in a new terminal window natively.
    # This avoids AppleScript Automation permission issues that cause silent failures
    # when osascript is invoked from a background server process.
    try:
        fd, script_path = tempfile.mkstemp(suffix=".command")
        with os.fdopen(fd, "w") as f:
            f.write("#!/bin/bash\n")
            f.write(f"{cmd}\n")
            # Clean up the temp file after the command finishes
            f.write(f"rm -f {shlex.quote(script_path)}\n")
        os.chmod(script_path, 0o755)
        subprocess.run(["open", "-a", "iTerm", script_path], capture_output=True, timeout=5)
        return {"ok": True}
    except Exception as e:
        return {"ok": False, "error": str(e)}
