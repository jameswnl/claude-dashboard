"""Data extraction from ~/.claude/projects/ directory."""

import hashlib
import json
import os
from pathlib import Path

from .utils import find_claude_md, format_date, project_display_name

PROJECTS_DIR = Path(os.environ.get("CLAUDE_PROJECTS_DIR", Path.home() / ".claude" / "projects"))


def extract_memory_files(project_path):
    memory_dir = project_path / "memory"
    files = []
    if memory_dir.is_dir():
        for mem_file in sorted(memory_dir.iterdir()):
            if mem_file.is_file() and not mem_file.name.startswith("."):
                try:
                    content = mem_file.read_text(errors="replace")
                    files.append({"name": mem_file.name, "content": content[:5000]})
                except Exception:
                    continue
    return files


def extract_sessions(project_path):
    sessions = []
    for jsonl_file in sorted(project_path.glob("*.jsonl")):
        session_id = jsonl_file.stem
        first_user_msg = ""
        user_messages = []
        timestamp = ""
        last_timestamp = ""
        msg_count = 0
        try:
            with open(jsonl_file, "r") as f:
                for line in f:
                    try:
                        d = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    if d.get("type") == "user" and d.get("message", {}).get("role") == "user":
                        msg_count += 1
                        content = d["message"].get("content", "")
                        text = ""
                        if isinstance(content, str):
                            text = content.strip()
                        elif isinstance(content, list):
                            for c in content:
                                if isinstance(c, dict) and c.get("type") == "text":
                                    text = c["text"].strip()
                                    break
                        if text:
                            if not first_user_msg:
                                first_user_msg = text[:300]
                            user_messages.append(text[:200])
                        if not timestamp and d.get("timestamp"):
                            timestamp = d["timestamp"]
                    if d.get("timestamp"):
                        last_timestamp = d["timestamp"]
        except Exception:
            continue
        if first_user_msg or timestamp:
            sessions.append({
                "id": session_id,
                "first_message": first_user_msg or "(no message)",
                "user_messages": user_messages,
                "started": timestamp,
                "last_activity": last_timestamp,
                "message_count": msg_count,
            })
    sessions.sort(key=lambda s: s.get("started", ""), reverse=True)
    return sessions


def collect_data():
    projects_data = []
    if not PROJECTS_DIR.is_dir():
        return projects_data
    for project_dir in sorted(PROJECTS_DIR.iterdir()):
        if not project_dir.is_dir():
            continue
        name = project_display_name(project_dir.name)
        sessions = extract_sessions(project_dir)
        memory_files = extract_memory_files(project_dir)
        claude_md = find_claude_md(project_dir.name)
        for s in sessions:
            s["started"] = format_date(s["started"])
            s["last_activity"] = format_date(s["last_activity"])
        projects_data.append({
            "name": name,
            "dirname": project_dir.name,
            "sessions": sessions,
            "has_memory": len(memory_files) > 0,
            "memory_files": memory_files,
            "claude_md": claude_md,
        })
    projects_data.sort(key=lambda p: len(p["sessions"]), reverse=True)
    return projects_data


def get_dir_fingerprint():
    """Get a hash of mtimes of all relevant files to detect changes."""
    parts = []
    try:
        for project_dir in sorted(PROJECTS_DIR.iterdir()):
            if not project_dir.is_dir():
                continue
            for f in project_dir.glob("*.jsonl"):
                try:
                    parts.append(f"{f}:{f.stat().st_mtime}")
                except OSError:
                    pass
            mem_dir = project_dir / "memory"
            if mem_dir.is_dir():
                for f in mem_dir.iterdir():
                    try:
                        parts.append(f"{f}:{f.stat().st_mtime}")
                    except OSError:
                        pass
            # Check CLAUDE.md in project dir
            real_path = "/" + project_dir.name.lstrip("-").replace("-", "/")
            claude_md = Path(real_path) / "CLAUDE.md"
            if claude_md.exists():
                try:
                    parts.append(f"{claude_md}:{claude_md.stat().st_mtime}")
                except OSError:
                    pass
    except Exception:
        pass
    return hashlib.md5("|".join(parts).encode()).hexdigest()
