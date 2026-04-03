"""Data extraction from ~/.claude/projects/ directory."""

import hashlib
import json
import os
from pathlib import Path

from .utils import dirname_to_path, find_claude_md, format_date, project_display_name

PROJECTS_DIR = Path(os.environ.get("CLAUDE_PROJECTS_DIR", Path.home() / ".claude" / "projects"))
CLAUDE_DIR = Path.home() / ".claude"


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


def _read_skill_file(filepath):
    """Read a skill/command .md file and return its metadata."""
    try:
        content = filepath.read_text(errors="replace")[:3000]
        return {"name": filepath.stem, "content": content}
    except Exception:
        return None


def _extract_plugin_meta(plugin_dir):
    """Extract metadata from a plugin directory (README, source URL)."""
    import re
    meta = {"name": plugin_dir.name}
    readme = plugin_dir / "README.md"
    if readme.exists():
        try:
            text = readme.read_text(errors="replace")[:5000]
            # Extract first GitHub URL as source
            urls = re.findall(r'https://github\.com/[^\s)"\]]+', text)
            if urls:
                meta["source_url"] = urls[0]
            # Extract first line as description
            for line in text.splitlines():
                line = line.strip().lstrip("#").strip()
                if line and not line.startswith("[") and not line.startswith("!"):
                    meta["description"] = line[:200]
                    break
        except Exception:
            pass
    return meta


def _extract_commands_from_dir(commands_dir):
    """Extract skill files from a commands directory."""
    skills = []
    if not commands_dir.is_dir():
        return skills
    for f in sorted(commands_dir.iterdir()):
        if f.is_file() and f.suffix == ".md":
            skill = _read_skill_file(f)
            if skill:
                skills.append(skill)
    return skills


def extract_project_skills(project_dirname):
    """Extract skills from a project's .claude/commands/ directory.

    Skips if the commands dir is the same as the user-level commands dir
    (e.g. when the project is the home directory).
    """
    project_path = dirname_to_path(project_dirname)
    commands_dir = Path(project_path) / ".claude" / "commands"
    user_commands = CLAUDE_DIR / "commands"
    if commands_dir.resolve() == user_commands.resolve():
        return []
    return _extract_commands_from_dir(commands_dir)


def collect_all_skills():
    """Collect skills from all sources: user-level, project-level, and plugins."""
    result = {"user": [], "projects": [], "plugins": []}

    # User-level commands
    user_commands = CLAUDE_DIR / "commands"
    result["user"] = _extract_commands_from_dir(user_commands)

    # Project-level commands (scan known project dirs)
    if PROJECTS_DIR.is_dir():
        seen = set()
        for project_dir in sorted(PROJECTS_DIR.iterdir()):
            if not project_dir.is_dir():
                continue
            project_path = dirname_to_path(project_dir.name)
            commands_dir = Path(project_path) / ".claude" / "commands"
            # Skip if same as user-level commands (e.g. home dir project)
            if commands_dir.resolve() == user_commands.resolve():
                continue
            if commands_dir.is_dir() and project_path not in seen:
                seen.add(project_path)
                skills = _extract_commands_from_dir(commands_dir)
                if skills:
                    result["projects"].append({
                        "name": project_display_name(project_dir.name),
                        "dirname": project_dir.name,
                        "skills": skills,
                    })

    # Plugin commands
    plugins_dir = CLAUDE_DIR / "plugins" / "marketplaces"
    if plugins_dir.is_dir():
        for marketplace in sorted(plugins_dir.iterdir()):
            plugins_path = marketplace / "plugins"
            if not plugins_path.is_dir():
                continue
            for plugin_dir in sorted(plugins_path.iterdir()):
                commands_dir = plugin_dir / "commands"
                if commands_dir.is_dir():
                    skills = _extract_commands_from_dir(commands_dir)
                    if skills:
                        meta = _extract_plugin_meta(plugin_dir)
                        meta["marketplace"] = marketplace.name
                        meta["skills"] = skills
                        result["plugins"].append(meta)

    return result


def _read_agent_file(filepath):
    """Read an agent .md file and return its metadata from YAML frontmatter."""
    try:
        content = filepath.read_text(errors="replace")[:5000]
        meta = {"name": filepath.stem, "content": content}
        # Parse YAML frontmatter
        if content.startswith("---"):
            parts = content.split("---", 2)
            if len(parts) >= 3:
                frontmatter = parts[1].strip()
                body = parts[2].strip()
                for line in frontmatter.splitlines():
                    if ":" in line:
                        key, _, val = line.partition(":")
                        key = key.strip()
                        val = val.strip().strip('"').strip("'")
                        if key in ("name", "description", "model", "color", "memory"):
                            meta[key] = val
                meta["body"] = body[:3000]
        return meta
    except OSError:
        return None


def _extract_agents_from_dir(agents_dir):
    """Extract agent files from a directory."""
    agents = []
    if not agents_dir.is_dir():
        return agents
    for f in sorted(agents_dir.iterdir()):
        if f.is_file() and f.suffix == ".md":
            agent = _read_agent_file(f)
            if agent:
                agents.append(agent)
    return agents


def collect_all_agents():
    """Collect agents from user-level and project-level sources."""
    result = {"user": [], "projects": []}

    # User-level agents
    user_agents = CLAUDE_DIR / "agents"
    result["user"] = _extract_agents_from_dir(user_agents)

    # Project-level agents
    if PROJECTS_DIR.is_dir():
        seen = set()
        for project_dir in sorted(PROJECTS_DIR.iterdir()):
            if not project_dir.is_dir():
                continue
            project_path = dirname_to_path(project_dir.name)
            agents_dir = Path(project_path) / ".claude" / "agents"
            # Skip if same as user-level agents (e.g. home dir project)
            if agents_dir.resolve() == user_agents.resolve():
                continue
            if agents_dir.is_dir() and project_path not in seen:
                seen.add(project_path)
                agents = _extract_agents_from_dir(agents_dir)
                if agents:
                    result["projects"].append({
                        "name": project_display_name(project_dir.name),
                        "dirname": project_dir.name,
                        "agents": agents,
                    })

    return result


_SECRET_KEYS = {"authorization", "token", "secret", "key", "password", "cookie", "api-key", "apikey"}


def _mask_value(value):
    """Mask a secret value, showing only first 8 chars."""
    s = str(value)
    if len(s) <= 8:
        return "****"
    return s[:8] + "****"


def _is_secret_header(key):
    """Check if a header key likely contains a secret."""
    lower = key.lower()
    return any(s in lower for s in _SECRET_KEYS)


def _read_mcp_servers(filepath):
    """Read MCP server configs from a JSON file."""
    try:
        data = json.loads(filepath.read_text(errors="replace"))
        servers = data.get("mcpServers", {})
        if not isinstance(servers, dict):
            return {}
        result = {}
        for name, cfg in servers.items():
            if not isinstance(cfg, dict):
                continue
            entry = {"name": name, "type": cfg.get("type", "unknown")}
            if "url" in cfg:
                entry["url"] = cfg["url"]
            if "command" in cfg:
                entry["command"] = cfg["command"]
            if "args" in cfg:
                entry["args"] = cfg["args"]
            if "env" in cfg and isinstance(cfg["env"], dict):
                entry["env"] = {k: _mask_value(v) for k, v in cfg["env"].items()}
            if "headers" in cfg and isinstance(cfg["headers"], dict):
                entry["headers"] = {
                    k: (_mask_value(v) if _is_secret_header(k) else v)
                    for k, v in cfg["headers"].items()
                }
            result[name] = entry
        return result
    except Exception:
        return {}


def collect_mcp_servers():
    """Collect MCP servers from user-level and project-level configs."""
    result = {"user": [], "projects": []}

    # User-level: ~/.claude.json
    user_config = Path.home() / ".claude.json"
    user_servers = _read_mcp_servers(user_config)
    result["user"] = list(user_servers.values())

    # Project-level: <project_path>/.mcp.json
    if PROJECTS_DIR.is_dir():
        seen = set()
        for project_dir in sorted(PROJECTS_DIR.iterdir()):
            if not project_dir.is_dir():
                continue
            project_path = dirname_to_path(project_dir.name)
            if project_path in seen:
                continue
            seen.add(project_path)
            mcp_file = Path(project_path) / ".mcp.json"
            if mcp_file.is_file():
                servers = _read_mcp_servers(mcp_file)
                if servers:
                    result["projects"].append({
                        "name": project_display_name(project_dir.name),
                        "dirname": project_dir.name,
                        "servers": list(servers.values()),
                    })

    return result


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
        skills = extract_project_skills(project_dir.name)
        project_path = dirname_to_path(project_dir.name)
        mcp_file = Path(project_path) / ".mcp.json"
        mcp_servers = list(_read_mcp_servers(mcp_file).values()) if mcp_file.is_file() else []
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
            "skills": skills,
            "mcp_servers": mcp_servers,
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
    # Track user-level agent files
    try:
        user_agents_dir = CLAUDE_DIR / "agents"
        if user_agents_dir.is_dir():
            for f in sorted(user_agents_dir.iterdir()):
                if f.is_file() and f.suffix == ".md":
                    try:
                        parts.append(f"{f}:{f.stat().st_mtime}")
                    except OSError:
                        pass
    except Exception:
        pass
    # Track project-level agent files
    try:
        for project_dir in sorted(PROJECTS_DIR.iterdir()):
            if not project_dir.is_dir():
                continue
            project_path = dirname_to_path(project_dir.name)
            agents_dir = Path(project_path) / ".claude" / "agents"
            if agents_dir.is_dir():
                for f in sorted(agents_dir.iterdir()):
                    if f.is_file() and f.suffix == ".md":
                        try:
                            parts.append(f"{f}:{f.stat().st_mtime}")
                        except OSError:
                            pass
    except Exception:
        pass
    return hashlib.md5("|".join(parts).encode()).hexdigest()
