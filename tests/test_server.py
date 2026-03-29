import json
import threading
import urllib.request
from pathlib import Path
from http.server import HTTPServer

from claude_dashboard.server import (
    DashboardHandler,
    DashboardState,
    get_state,
)
from claude_dashboard.data import (
    _extract_commands_from_dir,
    _extract_plugin_meta,
    _read_skill_file,
    collect_all_skills,
    collect_data,
    extract_memory_files,
    extract_sessions,
    get_dir_fingerprint,
)
from claude_dashboard.ui import get_html
from claude_dashboard.utils import (
    dirname_to_path,
    find_claude_md,
    format_date,
    open_terminal_with_session,
    project_display_name,
    read_claude_md,
)


# --- project_display_name ---

def _home_prefix():
    """Build the dirname prefix matching Path.home()."""
    from pathlib import Path
    return "-" + str(Path.home()).lstrip("/").replace("/", "-")


def test_project_display_name_with_subpath():
    dirname = _home_prefix() + "-ws-jira"
    assert project_display_name(dirname) == "~/ws/jira"


def test_project_display_name_home():
    dirname = _home_prefix()
    assert project_display_name(dirname) == "~"


def test_project_display_name_deep_path():
    dirname = _home_prefix() + "-ws-some-project"
    assert project_display_name(dirname) == "~/ws/some/project"


def test_project_display_name_unknown_prefix():
    assert project_display_name("-other-random-path") == "/other/random/path"


# --- format_date ---

def test_format_date_iso():
    assert format_date("2026-03-05T22:52:10.332Z") == "2026-03-05 22:52"


def test_format_date_empty():
    assert format_date("") == ""
    assert format_date(None) == ""


def test_format_date_malformed():
    result = format_date("not-a-date")
    assert isinstance(result, str)


# --- extract_sessions ---

def test_extract_sessions_empty_dir(tmp_path):
    sessions = extract_sessions(tmp_path)
    assert sessions == []


def test_extract_sessions_with_jsonl(tmp_path):
    session_data = [
        {
            "type": "user",
            "message": {"role": "user", "content": "hello world"},
            "timestamp": "2026-03-05T10:00:00Z",
            "sessionId": "test-session",
        },
        {
            "type": "assistant",
            "message": {"role": "assistant", "content": [{"type": "text", "text": "hi"}]},
            "timestamp": "2026-03-05T10:00:05Z",
            "sessionId": "test-session",
        },
        {
            "type": "user",
            "message": {"role": "user", "content": "second message"},
            "timestamp": "2026-03-05T10:01:00Z",
            "sessionId": "test-session",
        },
    ]
    jsonl_file = tmp_path / "test-session.jsonl"
    jsonl_file.write_text("\n".join(json.dumps(d) for d in session_data))

    sessions = extract_sessions(tmp_path)
    assert len(sessions) == 1
    assert sessions[0]["first_message"] == "hello world"
    assert sessions[0]["message_count"] == 2
    assert len(sessions[0]["user_messages"]) == 2


def test_extract_sessions_with_list_content(tmp_path):
    session_data = [
        {
            "type": "user",
            "message": {
                "role": "user",
                "content": [{"type": "text", "text": "list format message"}],
            },
            "timestamp": "2026-03-05T10:00:00Z",
            "sessionId": "test",
        },
    ]
    jsonl_file = tmp_path / "test.jsonl"
    jsonl_file.write_text(json.dumps(session_data[0]))

    sessions = extract_sessions(tmp_path)
    assert sessions[0]["first_message"] == "list format message"


def test_extract_sessions_skips_invalid_json(tmp_path):
    jsonl_file = tmp_path / "bad.jsonl"
    jsonl_file.write_text(
        "not json\n"
        + json.dumps({
            "type": "user",
            "message": {"role": "user", "content": "valid"},
            "timestamp": "2026-01-01T00:00:00Z",
            "sessionId": "s",
        })
    )
    sessions = extract_sessions(tmp_path)
    assert len(sessions) == 1
    assert sessions[0]["first_message"] == "valid"


def test_extract_sessions_timestamp_only(tmp_path):
    """Session with timestamp but no user message text gets '(no message)'."""
    data = {
        "type": "user",
        "message": {"role": "user", "content": ""},
        "timestamp": "2026-01-01T00:00:00Z",
        "sessionId": "s",
    }
    (tmp_path / "s.jsonl").write_text(json.dumps(data))
    sessions = extract_sessions(tmp_path)
    assert len(sessions) == 1
    assert sessions[0]["first_message"] == "(no message)"


def test_extract_sessions_last_activity(tmp_path):
    """last_activity should be the timestamp of the last line."""
    lines = [
        {"type": "user", "message": {"role": "user", "content": "hi"},
         "timestamp": "2026-01-01T00:00:00Z", "sessionId": "s"},
        {"type": "assistant", "message": {"role": "assistant", "content": "bye"},
         "timestamp": "2026-01-01T01:00:00Z", "sessionId": "s"},
    ]
    (tmp_path / "s.jsonl").write_text("\n".join(json.dumps(l) for l in lines))
    sessions = extract_sessions(tmp_path)
    assert sessions[0]["last_activity"] == "2026-01-01T01:00:00Z"


# --- extract_memory_files ---

def test_extract_memory_files_empty(tmp_path):
    assert extract_memory_files(tmp_path) == []


def test_extract_memory_files_with_files(tmp_path):
    mem_dir = tmp_path / "memory"
    mem_dir.mkdir()
    (mem_dir / "MEMORY.md").write_text("# Project notes\nSome content here")
    (mem_dir / "patterns.md").write_text("Pattern 1\nPattern 2")
    (mem_dir / ".hidden").write_text("should be ignored")

    files = extract_memory_files(tmp_path)
    assert len(files) == 2
    names = [f["name"] for f in files]
    assert "MEMORY.md" in names
    assert "patterns.md" in names
    assert ".hidden" not in names


def test_extract_memory_files_truncates(tmp_path):
    mem_dir = tmp_path / "memory"
    mem_dir.mkdir()
    (mem_dir / "big.md").write_text("x" * 10000)

    files = extract_memory_files(tmp_path)
    assert len(files[0]["content"]) == 5000


# --- find_claude_md ---

def test_dirname_to_path():
    assert dirname_to_path("-a-b-c") == "/a/b/c"
    assert dirname_to_path("-home-user-projects") == "/home/user/projects"


def test_read_claude_md_exists(tmp_path):
    (tmp_path / "CLAUDE.md").write_text("# Instructions\nDo stuff")
    result = read_claude_md(tmp_path)
    assert result == "# Instructions\nDo stuff"


def test_read_claude_md_not_exists(tmp_path):
    result = read_claude_md(tmp_path)
    assert result is None


def test_read_claude_md_truncates(tmp_path):
    (tmp_path / "CLAUDE.md").write_text("x" * 10000)
    result = read_claude_md(tmp_path)
    assert len(result) == 8000


def test_find_claude_md_not_exists():
    result = find_claude_md("-nonexistent-path-that-does-not-exist")
    assert result is None


# --- get_html ---

def test_get_html_returns_valid_html():
    html = get_html()
    assert "<!DOCTYPE html>" in html
    assert "Claude Code Dashboard" in html
    assert "/api/data" in html


# --- get_dir_fingerprint ---

def test_get_dir_fingerprint_returns_string(tmp_path, monkeypatch):
    monkeypatch.setattr("claude_dashboard.data.PROJECTS_DIR", tmp_path)
    fp = get_dir_fingerprint()
    assert isinstance(fp, str)
    assert len(fp) == 32  # md5 hex digest


def test_get_dir_fingerprint_changes_on_new_file(tmp_path, monkeypatch):
    monkeypatch.setattr("claude_dashboard.data.PROJECTS_DIR", tmp_path)
    project = tmp_path / "test-project"
    project.mkdir()

    fp1 = get_dir_fingerprint()
    (project / "session.jsonl").write_text("{}")
    fp2 = get_dir_fingerprint()
    assert fp1 != fp2


def test_get_dir_fingerprint_detects_memory_change(tmp_path, monkeypatch):
    monkeypatch.setattr("claude_dashboard.data.PROJECTS_DIR", tmp_path)
    project = tmp_path / "test-project"
    project.mkdir()
    mem_dir = project / "memory"
    mem_dir.mkdir()

    fp1 = get_dir_fingerprint()
    (mem_dir / "MEMORY.md").write_text("new memory")
    fp2 = get_dir_fingerprint()
    assert fp1 != fp2


def test_get_dir_fingerprint_skips_non_dirs(tmp_path, monkeypatch):
    monkeypatch.setattr("claude_dashboard.data.PROJECTS_DIR", tmp_path)
    (tmp_path / "somefile.txt").write_text("not a dir")
    fp = get_dir_fingerprint()
    assert isinstance(fp, str)


# --- sessions sorting ---

def test_sessions_sorted_most_recent_first(tmp_path):
    for i, ts in enumerate(["2026-01-01T00:00:00Z", "2026-06-01T00:00:00Z", "2026-03-01T00:00:00Z"]):
        data = {
            "type": "user",
            "message": {"role": "user", "content": f"msg {i}"},
            "timestamp": ts,
            "sessionId": f"s{i}",
        }
        (tmp_path / f"session{i}.jsonl").write_text(json.dumps(data))

    sessions = extract_sessions(tmp_path)
    timestamps = [s["started"] for s in sessions]
    assert timestamps == sorted(timestamps, reverse=True)


# --- collect_data ---

def test_collect_data_missing_dir(tmp_path, monkeypatch):
    monkeypatch.setattr("claude_dashboard.data.PROJECTS_DIR", tmp_path / "nonexistent")
    result = collect_data()
    assert result == []


def test_collect_data_with_projects(tmp_path, monkeypatch):
    monkeypatch.setattr("claude_dashboard.data.PROJECTS_DIR", tmp_path)

    home_prefix = _home_prefix()

    # Create two projects, one with more sessions
    proj1 = tmp_path / (home_prefix + "-ws-alpha")
    proj1.mkdir()
    for i in range(3):
        data = {"type": "user", "message": {"role": "user", "content": f"msg {i}"},
                "timestamp": f"2026-01-0{i+1}T00:00:00Z", "sessionId": f"s{i}"}
        (proj1 / f"s{i}.jsonl").write_text(json.dumps(data))

    proj2 = tmp_path / (home_prefix + "-ws-beta")
    proj2.mkdir()
    data = {"type": "user", "message": {"role": "user", "content": "hello"},
            "timestamp": "2026-02-01T00:00:00Z", "sessionId": "s0"}
    (proj2 / "s0.jsonl").write_text(json.dumps(data))

    result = collect_data()
    assert len(result) == 2
    # Sorted by session count descending
    assert result[0]["name"] == "~/ws/alpha"
    assert len(result[0]["sessions"]) == 3
    assert result[1]["name"] == "~/ws/beta"
    # Dates should be formatted
    assert "2026-" in result[0]["sessions"][0]["started"]


def test_collect_data_skips_files(tmp_path, monkeypatch):
    monkeypatch.setattr("claude_dashboard.data.PROJECTS_DIR", tmp_path)
    (tmp_path / "not-a-dir.txt").write_text("file")
    result = collect_data()
    assert result == []


def test_collect_data_includes_memory(tmp_path, monkeypatch):
    monkeypatch.setattr("claude_dashboard.data.PROJECTS_DIR", tmp_path)
    proj = tmp_path / (_home_prefix() + "-ws-test")
    proj.mkdir()
    mem = proj / "memory"
    mem.mkdir()
    (mem / "MEMORY.md").write_text("notes")

    result = collect_data()
    assert result[0]["has_memory"] is True
    assert len(result[0]["memory_files"]) == 1


# --- DashboardState ---

def test_dashboard_state(tmp_path, monkeypatch):
    monkeypatch.setattr("claude_dashboard.data.PROJECTS_DIR", tmp_path)
    s = DashboardState()
    data_json, skills_json, version = s.get()
    assert version == 1
    assert json.loads(data_json) == []

    # Create a project and refresh
    proj = tmp_path / (_home_prefix() + "-ws-x")
    proj.mkdir()
    d = {"type": "user", "message": {"role": "user", "content": "hi"},
         "timestamp": "2026-01-01T00:00:00Z", "sessionId": "s"}
    (proj / "s.jsonl").write_text(json.dumps(d))
    s.refresh()

    data_json, skills_json, version = s.get()
    assert version == 2
    data = json.loads(data_json)
    assert len(data) == 1


# --- get_state ---

def test_get_state_lazy_init(tmp_path, monkeypatch):
    import claude_dashboard.server as mod
    monkeypatch.setattr("claude_dashboard.data.PROJECTS_DIR", tmp_path)
    monkeypatch.setattr(mod, "state", None)
    s = get_state()
    assert s is not None
    # Calling again returns the same instance
    assert get_state() is s


# --- DashboardHandler (HTTP) ---

def test_handler_serves_html(tmp_path, monkeypatch):
    import claude_dashboard.server as mod
    monkeypatch.setattr("claude_dashboard.data.PROJECTS_DIR", tmp_path)
    monkeypatch.setattr(mod, "state", None)

    server = HTTPServer(("127.0.0.1", 0), DashboardHandler)
    port = server.server_address[1]
    t = threading.Thread(target=server.handle_request, daemon=True)
    t.start()

    resp = urllib.request.urlopen(f"http://127.0.0.1:{port}/")
    body = resp.read().decode()
    assert resp.status == 200
    assert "Claude Code Dashboard" in body
    server.server_close()


def test_handler_serves_api_data(tmp_path, monkeypatch):
    import claude_dashboard.server as mod
    monkeypatch.setattr("claude_dashboard.data.PROJECTS_DIR", tmp_path)
    monkeypatch.setattr(mod, "state", None)

    server = HTTPServer(("127.0.0.1", 0), DashboardHandler)
    port = server.server_address[1]
    t = threading.Thread(target=server.handle_request, daemon=True)
    t.start()

    resp = urllib.request.urlopen(f"http://127.0.0.1:{port}/api/data")
    body = json.loads(resp.read())
    assert resp.status == 200
    assert "version" in body
    assert "data" in body
    assert isinstance(body["data"], list)
    server.server_close()


def test_handler_404(tmp_path, monkeypatch):
    import claude_dashboard.server as mod
    monkeypatch.setattr("claude_dashboard.data.PROJECTS_DIR", tmp_path)
    monkeypatch.setattr(mod, "state", None)

    server = HTTPServer(("127.0.0.1", 0), DashboardHandler)
    port = server.server_address[1]
    t = threading.Thread(target=server.handle_request, daemon=True)
    t.start()

    try:
        urllib.request.urlopen(f"http://127.0.0.1:{port}/nonexistent")
        assert False, "Should have raised"
    except urllib.error.HTTPError as e:
        assert e.code == 404
    server.server_close()


# --- dirname_to_path with filesystem probing ---

def test_dirname_to_path_empty():
    assert dirname_to_path("-") == "/"


def test_dirname_to_path_probes_filesystem(tmp_path, monkeypatch):
    """dirname_to_path should find hyphenated directories via filesystem probing."""
    # Create a hyphenated directory
    (tmp_path / "my-project").mkdir()
    # Build a dirname that includes tmp_path
    parts = str(tmp_path).lstrip("/").split("/")
    dirname = "-" + "-".join(parts) + "-my-project"
    result = dirname_to_path(dirname)
    assert result == str(tmp_path / "my-project")


# --- open_terminal_with_session ---

def test_open_terminal_with_session_nonexistent_dir(monkeypatch):
    """When directory doesn't exist, should still return ok (runs without cd)."""
    # Mock subprocess.run to capture the call
    calls = []
    def mock_run(*args, **kwargs):
        calls.append(args)
        raise Exception("no osascript in test")
    monkeypatch.setattr("claude_dashboard.utils.subprocess.run", mock_run)
    result = open_terminal_with_session("test-session-id", "-nonexistent-path")
    # Should have tried both iTerm and Terminal, both failed
    assert result["ok"] is False
    assert "error" in result
    assert len(calls) == 2  # tried iTerm2 and Terminal


def test_open_terminal_with_session_success(tmp_path, monkeypatch):
    """When osascript succeeds, should return ok."""
    import subprocess as sp
    def mock_run(*args, **kwargs):
        return sp.CompletedProcess(args=args, returncode=0)
    monkeypatch.setattr("claude_dashboard.utils.subprocess.run", mock_run)
    # Use a dirname that resolves to tmp_path
    parts = str(tmp_path).lstrip("/").split("/")
    dirname = "-" + "-".join(parts)
    result = open_terminal_with_session("test-session", dirname)
    assert result["ok"] is True


# --- POST /api/refresh ---

def test_handler_post_refresh(tmp_path, monkeypatch):
    import claude_dashboard.server as mod
    monkeypatch.setattr("claude_dashboard.data.PROJECTS_DIR", tmp_path)
    monkeypatch.setattr(mod, "state", None)

    server = HTTPServer(("127.0.0.1", 0), DashboardHandler)
    port = server.server_address[1]
    t = threading.Thread(target=server.handle_request, daemon=True)
    t.start()

    req = urllib.request.Request(
        f"http://127.0.0.1:{port}/api/refresh", method="POST", data=b""
    )
    resp = urllib.request.urlopen(req)
    body = json.loads(resp.read())
    assert resp.status == 200
    assert body["ok"] is True
    server.server_close()


# --- POST /api/resume ---

def test_handler_post_resume(tmp_path, monkeypatch):
    import claude_dashboard.server as mod
    monkeypatch.setattr("claude_dashboard.data.PROJECTS_DIR", tmp_path)
    monkeypatch.setattr(mod, "state", None)

    # Mock open_terminal_with_session
    monkeypatch.setattr(
        "claude_dashboard.server.open_terminal_with_session",
        lambda sid, dn: {"ok": True},
    )

    server = HTTPServer(("127.0.0.1", 0), DashboardHandler)
    port = server.server_address[1]
    t = threading.Thread(target=server.handle_request, daemon=True)
    t.start()

    data = json.dumps({"session_id": "abc", "dirname": "-test"}).encode()
    req = urllib.request.Request(
        f"http://127.0.0.1:{port}/api/resume",
        method="POST",
        data=data,
        headers={"Content-Type": "application/json"},
    )
    resp = urllib.request.urlopen(req)
    body = json.loads(resp.read())
    assert resp.status == 200
    assert body["ok"] is True
    server.server_close()


# --- POST 404 ---

def test_handler_post_404(tmp_path, monkeypatch):
    import claude_dashboard.server as mod
    monkeypatch.setattr("claude_dashboard.data.PROJECTS_DIR", tmp_path)
    monkeypatch.setattr(mod, "state", None)

    server = HTTPServer(("127.0.0.1", 0), DashboardHandler)
    port = server.server_address[1]
    t = threading.Thread(target=server.handle_request, daemon=True)
    t.start()

    req = urllib.request.Request(
        f"http://127.0.0.1:{port}/nonexistent", method="POST", data=b""
    )
    try:
        urllib.request.urlopen(req)
        assert False, "Should have raised"
    except urllib.error.HTTPError as e:
        assert e.code == 404
    server.server_close()


# --- get_html search features ---

def test_get_html_has_search_toggles():
    html = get_html()
    assert "toggle-case" in html
    assert "toggle-word" in html
    assert "search-clear" in html


# --- Skills ---

def test_read_skill_file(tmp_path):
    skill_file = tmp_path / "my-skill.md"
    skill_file.write_text("Do something useful")
    result = _read_skill_file(skill_file)
    assert result["name"] == "my-skill"
    assert result["content"] == "Do something useful"


def test_read_skill_file_truncates(tmp_path):
    skill_file = tmp_path / "big.md"
    skill_file.write_text("x" * 5000)
    result = _read_skill_file(skill_file)
    assert len(result["content"]) == 3000


def test_extract_commands_from_dir_empty(tmp_path):
    assert _extract_commands_from_dir(tmp_path) == []


def test_extract_commands_from_dir_with_files(tmp_path):
    (tmp_path / "skill-a.md").write_text("Skill A")
    (tmp_path / "skill-b.md").write_text("Skill B")
    (tmp_path / "not-a-skill.txt").write_text("ignored")
    result = _extract_commands_from_dir(tmp_path)
    assert len(result) == 2
    names = [s["name"] for s in result]
    assert "skill-a" in names
    assert "skill-b" in names


def test_extract_commands_from_dir_nonexistent(tmp_path):
    assert _extract_commands_from_dir(tmp_path / "nope") == []


def test_collect_all_skills_empty(tmp_path, monkeypatch):
    monkeypatch.setattr("claude_dashboard.data.CLAUDE_DIR", tmp_path / "claude")
    monkeypatch.setattr("claude_dashboard.data.PROJECTS_DIR", tmp_path / "projects")
    result = collect_all_skills()
    assert result["user"] == []
    assert result["projects"] == []
    assert result["plugins"] == []


def test_collect_all_skills_with_user_skills(tmp_path, monkeypatch):
    claude_dir = tmp_path / "claude"
    claude_dir.mkdir()
    commands = claude_dir / "commands"
    commands.mkdir()
    (commands / "my-cmd.md").write_text("User command")
    monkeypatch.setattr("claude_dashboard.data.CLAUDE_DIR", claude_dir)
    monkeypatch.setattr("claude_dashboard.data.PROJECTS_DIR", tmp_path / "projects")
    result = collect_all_skills()
    assert len(result["user"]) == 1
    assert result["user"][0]["name"] == "my-cmd"


def test_collect_all_skills_with_plugins(tmp_path, monkeypatch):
    claude_dir = tmp_path / "claude"
    claude_dir.mkdir()
    marketplace = claude_dir / "plugins" / "marketplaces" / "official" / "plugins" / "my-plugin" / "commands"
    marketplace.mkdir(parents=True)
    (marketplace / "do-thing.md").write_text("Plugin skill")
    monkeypatch.setattr("claude_dashboard.data.CLAUDE_DIR", claude_dir)
    monkeypatch.setattr("claude_dashboard.data.PROJECTS_DIR", tmp_path / "projects")
    result = collect_all_skills()
    assert len(result["plugins"]) == 1
    assert result["plugins"][0]["name"] == "my-plugin"
    assert result["plugins"][0]["skills"][0]["name"] == "do-thing"


def test_get_html_has_skills_view():
    html = get_html()
    assert "view-skills" in html
    assert "skills-content" in html


def test_api_data_includes_skills(tmp_path, monkeypatch):
    import claude_dashboard.server as mod
    monkeypatch.setattr("claude_dashboard.data.PROJECTS_DIR", tmp_path)
    monkeypatch.setattr("claude_dashboard.data.CLAUDE_DIR", tmp_path / "claude")
    monkeypatch.setattr(mod, "state", None)

    server = HTTPServer(("127.0.0.1", 0), DashboardHandler)
    port = server.server_address[1]
    t = threading.Thread(target=server.handle_request, daemon=True)
    t.start()

    resp = urllib.request.urlopen(f"http://127.0.0.1:{port}/api/data")
    body = json.loads(resp.read())
    assert "skills" in body
    assert "user" in body["skills"]
    assert "projects" in body["skills"]
    assert "plugins" in body["skills"]
    server.server_close()


# --- Additional coverage tests ---


# data.py: extract_memory_files exception branch (lines 23-24)
def test_extract_memory_files_read_error(tmp_path, monkeypatch):
    """Memory file that raises on read_text should be skipped."""
    mem_dir = tmp_path / "memory"
    mem_dir.mkdir()
    f = mem_dir / "good.md"
    f.write_text("good content")
    bad = mem_dir / "bad.md"
    bad.write_text("bad content")
    # Make bad.md unreadable by monkeypatching
    original_read_text = Path.read_text
    def patched_read_text(self, *args, **kwargs):
        if self.name == "bad.md":
            raise PermissionError("no access")
        return original_read_text(self, *args, **kwargs)
    monkeypatch.setattr(Path, "read_text", patched_read_text)
    files = extract_memory_files(tmp_path)
    assert len(files) == 1
    assert files[0]["name"] == "good.md"


# data.py: extract_sessions outer exception (lines 63-64)
def test_extract_sessions_file_open_error(tmp_path, monkeypatch):
    """If opening a jsonl file raises, that session is skipped."""
    good_data = {"type": "user", "message": {"role": "user", "content": "hello"},
                 "timestamp": "2026-01-01T00:00:00Z", "sessionId": "good"}
    (tmp_path / "good.jsonl").write_text(json.dumps(good_data))
    (tmp_path / "bad.jsonl").write_text("some data")

    # Make 'bad.jsonl' raise on open
    import builtins
    original_open = builtins.open
    def patched_open(path, *args, **kwargs):
        if str(path).endswith("bad.jsonl"):
            raise PermissionError("cannot open")
        return original_open(path, *args, **kwargs)
    monkeypatch.setattr(builtins, "open", patched_open)

    sessions = extract_sessions(tmp_path)
    assert len(sessions) == 1
    assert sessions[0]["id"] == "good"


# data.py: _read_skill_file exception (lines 83-84)
def test_read_skill_file_error(tmp_path, monkeypatch):
    """If reading a skill file fails, return None."""
    skill_file = tmp_path / "broken.md"
    skill_file.write_text("content")
    original_read_text = Path.read_text
    def patched_read_text(self, *args, **kwargs):
        if self.name == "broken.md":
            raise PermissionError("no access")
        return original_read_text(self, *args, **kwargs)
    monkeypatch.setattr(Path, "read_text", patched_read_text)
    result = _read_skill_file(skill_file)
    assert result is None


# data.py: extract_project_skills (lines 102-104)
def test_extract_project_skills(tmp_path):
    from claude_dashboard.data import extract_project_skills
    # Create a project directory with .claude/commands
    project_dir = tmp_path / "myproject"
    project_dir.mkdir()
    commands_dir = project_dir / ".claude" / "commands"
    commands_dir.mkdir(parents=True)
    (commands_dir / "cmd1.md").write_text("Command 1")

    # Build the dirname that resolves to this path
    parts = str(project_dir).lstrip("/").split("/")
    dirname = "-" + "-".join(parts)
    skills = extract_project_skills(dirname)
    assert len(skills) == 1
    assert skills[0]["name"] == "cmd1"


# data.py: collect_all_skills with project-level commands (lines 120, 124-127)
def test_collect_all_skills_with_project_skills(tmp_path, monkeypatch):
    """Test project-level skills in collect_all_skills."""
    claude_dir = tmp_path / "claude"
    claude_dir.mkdir()
    projects_dir = tmp_path / "projects"
    projects_dir.mkdir()

    # Create a real project directory with .claude/commands
    real_project = tmp_path / "real_project"
    real_project.mkdir()
    commands_dir = real_project / ".claude" / "commands"
    commands_dir.mkdir(parents=True)
    (commands_dir / "proj-cmd.md").write_text("Project command")

    # Create a project entry in projects_dir whose dirname resolves to real_project
    parts = str(real_project).lstrip("/").split("/")
    project_dirname = "-" + "-".join(parts)
    project_entry = projects_dir / project_dirname
    project_entry.mkdir()

    monkeypatch.setattr("claude_dashboard.data.CLAUDE_DIR", claude_dir)
    monkeypatch.setattr("claude_dashboard.data.PROJECTS_DIR", projects_dir)

    result = collect_all_skills()
    assert len(result["projects"]) == 1
    assert result["projects"][0]["skills"][0]["name"] == "proj-cmd"


# data.py: collect_all_skills skips non-dir in projects (line 120)
def test_collect_all_skills_skips_file_in_projects(tmp_path, monkeypatch):
    """Files in PROJECTS_DIR should be skipped."""
    claude_dir = tmp_path / "claude"
    claude_dir.mkdir()
    projects_dir = tmp_path / "projects"
    projects_dir.mkdir()
    (projects_dir / "not-a-dir.txt").write_text("file")
    monkeypatch.setattr("claude_dashboard.data.CLAUDE_DIR", claude_dir)
    monkeypatch.setattr("claude_dashboard.data.PROJECTS_DIR", projects_dir)
    result = collect_all_skills()
    assert result["projects"] == []


# data.py: plugin marketplace without plugins subdir (line 139)
def test_collect_all_skills_plugin_no_plugins_subdir(tmp_path, monkeypatch):
    """Marketplace dir without 'plugins' subdir should be skipped."""
    claude_dir = tmp_path / "claude"
    claude_dir.mkdir()
    marketplace = claude_dir / "plugins" / "marketplaces" / "official"
    marketplace.mkdir(parents=True)
    # No 'plugins' subdir inside marketplace
    (marketplace / "readme.txt").write_text("no plugins here")
    monkeypatch.setattr("claude_dashboard.data.CLAUDE_DIR", claude_dir)
    monkeypatch.setattr("claude_dashboard.data.PROJECTS_DIR", tmp_path / "projects")
    result = collect_all_skills()
    assert result["plugins"] == []


# data.py: get_dir_fingerprint OSError on jsonl stat (lines 189-190)
def test_get_dir_fingerprint_oserror_jsonl(tmp_path, monkeypatch):
    """OSError when stat-ing a jsonl file should be silently handled."""
    monkeypatch.setattr("claude_dashboard.data.PROJECTS_DIR", tmp_path)
    project = tmp_path / "test-project"
    project.mkdir()
    jsonl = project / "session.jsonl"
    jsonl.write_text("{}")

    # Make stat raise OSError for jsonl files
    original_stat = Path.stat
    def patched_stat(self, *args, **kwargs):
        if self.suffix == ".jsonl":
            raise OSError("stat failed")
        return original_stat(self, *args, **kwargs)
    monkeypatch.setattr(Path, "stat", patched_stat)

    fp = get_dir_fingerprint()
    assert isinstance(fp, str)
    assert len(fp) == 32


# data.py: get_dir_fingerprint OSError on memory file stat (lines 196-197)
def test_get_dir_fingerprint_oserror_memory(tmp_path, monkeypatch):
    """OSError when stat-ing a memory file should be silently handled."""
    monkeypatch.setattr("claude_dashboard.data.PROJECTS_DIR", tmp_path)
    project = tmp_path / "test-project"
    project.mkdir()
    mem_dir = project / "memory"
    mem_dir.mkdir()
    (mem_dir / "MEMORY.md").write_text("content")

    original_stat = Path.stat
    def patched_stat(self, *args, **kwargs):
        if self.parent.name == "memory":
            raise OSError("stat failed")
        return original_stat(self, *args, **kwargs)
    monkeypatch.setattr(Path, "stat", patched_stat)

    fp = get_dir_fingerprint()
    assert isinstance(fp, str)
    assert len(fp) == 32


# data.py: get_dir_fingerprint CLAUDE.md exists check (lines 202-207)
def test_get_dir_fingerprint_with_claude_md(tmp_path, monkeypatch):
    """Fingerprint should include CLAUDE.md from the real project path.

    get_dir_fingerprint uses: real_path = '/' + project_dir.name.lstrip('-').replace('-', '/')
    So we create a project dir named like '-real' which maps to '/real'.
    We then create /real/CLAUDE.md (needs root, so we mock Path.exists instead).
    """
    monkeypatch.setattr("claude_dashboard.data.PROJECTS_DIR", tmp_path)

    # Create a project subdir in PROJECTS_DIR
    project_entry = tmp_path / "-tmp-testproj"
    project_entry.mkdir()

    # The fingerprint code computes: real_path = "/" + "tmp-testproj" = "/tmp/testproj"
    # and checks Path("/tmp/testproj/CLAUDE.md").exists()
    # We need /tmp/testproj to exist with a CLAUDE.md
    import os
    test_proj = Path("/tmp/testproj")
    test_proj.mkdir(exist_ok=True)
    claude_md = test_proj / "CLAUDE.md"
    claude_md.write_text("instructions")

    try:
        fp1 = get_dir_fingerprint()

        import time
        time.sleep(0.05)
        claude_md.write_text("updated instructions")

        fp2 = get_dir_fingerprint()
        assert fp1 != fp2
    finally:
        claude_md.unlink(missing_ok=True)
        test_proj.rmdir()


# data.py: get_dir_fingerprint outer exception (lines 206-207)
def test_get_dir_fingerprint_outer_exception(tmp_path, monkeypatch):
    """If iterdir raises, fingerprint should still return a hash."""
    monkeypatch.setattr("claude_dashboard.data.PROJECTS_DIR", tmp_path)

    # Make PROJECTS_DIR.iterdir() raise
    def raise_error():
        raise RuntimeError("broken")
    monkeypatch.setattr(Path, "iterdir", lambda self: raise_error())

    fp = get_dir_fingerprint()
    assert isinstance(fp, str)
    assert len(fp) == 32


# data.py: collect_data includes claude_md
def test_collect_data_includes_claude_md(tmp_path, monkeypatch):
    """collect_data should include claude_md from find_claude_md."""
    monkeypatch.setattr("claude_dashboard.data.PROJECTS_DIR", tmp_path)

    # Use /tmp/testproj2 as the real project path
    import os
    test_proj = Path("/tmp/testproj2")
    test_proj.mkdir(exist_ok=True)
    (test_proj / "CLAUDE.md").write_text("# Project instructions")

    try:
        # dirname "-tmp-testproj2" resolves to /tmp/testproj2
        project_entry = tmp_path / "-tmp-testproj2"
        project_entry.mkdir()

        # Add a session so the project shows up
        data = {"type": "user", "message": {"role": "user", "content": "hi"},
                "timestamp": "2026-01-01T00:00:00Z", "sessionId": "s1"}
        (project_entry / "s1.jsonl").write_text(json.dumps(data))

        result = collect_data()
        assert len(result) == 1
        assert result[0]["claude_md"] == "# Project instructions"
    finally:
        (test_proj / "CLAUDE.md").unlink(missing_ok=True)
        test_proj.rmdir()


# utils.py: read_claude_md exception branch (lines 47-48)
def test_read_claude_md_exception(tmp_path, monkeypatch):
    """If read_text raises, return None."""
    (tmp_path / "CLAUDE.md").write_text("content")
    original_read_text = Path.read_text
    def patched_read_text(self, *args, **kwargs):
        if self.name == "CLAUDE.md":
            raise PermissionError("no access")
        return original_read_text(self, *args, **kwargs)
    monkeypatch.setattr(Path, "read_text", patched_read_text)
    result = read_claude_md(tmp_path)
    assert result is None


# utils.py: open_terminal_with_session - iTerm fails, Terminal succeeds (line 121)
def test_open_terminal_iterm_fails_terminal_succeeds(tmp_path, monkeypatch):
    """When iTerm2 fails but Terminal.app succeeds, return ok."""
    import subprocess as sp
    call_count = [0]
    def mock_run(*args, **kwargs):
        call_count[0] += 1
        if call_count[0] == 1:
            raise Exception("iTerm not found")
        return sp.CompletedProcess(args=args, returncode=0)
    monkeypatch.setattr("claude_dashboard.utils.subprocess.run", mock_run)
    parts = str(tmp_path).lstrip("/").split("/")
    dirname = "-" + "-".join(parts)
    result = open_terminal_with_session("test-session", dirname)
    assert result["ok"] is True
    assert call_count[0] == 2


# utils.py: dirname_to_path with empty string
def test_dirname_to_path_empty_string():
    """Empty dirname should still work."""
    result = dirname_to_path("")
    # "".lstrip("-").split("-") = [""] so parts is non-empty
    # The single empty part becomes path / "" which is just "/"
    assert result == "/"


# extract_sessions: content is list with non-text types
def test_extract_sessions_list_content_no_text(tmp_path):
    """List content without text type should not set first_message."""
    data = {
        "type": "user",
        "message": {"role": "user", "content": [{"type": "image", "url": "http://x"}]},
        "timestamp": "2026-01-01T00:00:00Z",
        "sessionId": "s",
    }
    (tmp_path / "s.jsonl").write_text(json.dumps(data))
    sessions = extract_sessions(tmp_path)
    assert len(sessions) == 1
    assert sessions[0]["first_message"] == "(no message)"


# extract_sessions: message without type=user should be ignored
def test_extract_sessions_non_user_type(tmp_path):
    """Non-user type entries with timestamps should still update last_timestamp."""
    lines = [
        {"type": "user", "message": {"role": "user", "content": "hi"},
         "timestamp": "2026-01-01T00:00:00Z"},
        {"type": "system", "timestamp": "2026-01-01T02:00:00Z"},
    ]
    (tmp_path / "s.jsonl").write_text("\n".join(json.dumps(l) for l in lines))
    sessions = extract_sessions(tmp_path)
    assert sessions[0]["last_activity"] == "2026-01-01T02:00:00Z"
    assert sessions[0]["message_count"] == 1


# extract_sessions: no first_message and no timestamp should skip
def test_extract_sessions_no_message_no_timestamp(tmp_path):
    """Session with no user message and no timestamp should be skipped."""
    data = {"type": "system", "info": "something"}
    (tmp_path / "s.jsonl").write_text(json.dumps(data))
    sessions = extract_sessions(tmp_path)
    assert sessions == []


# server.py: log_message is suppressed
def test_handler_log_message_suppressed(tmp_path, monkeypatch):
    """DashboardHandler.log_message should do nothing (suppress logs)."""
    import claude_dashboard.server as mod
    monkeypatch.setattr("claude_dashboard.data.PROJECTS_DIR", tmp_path)
    monkeypatch.setattr(mod, "state", None)
    handler = DashboardHandler.__new__(DashboardHandler)
    # Should not raise
    handler.log_message("test %s", "msg")


# --- _extract_plugin_meta ---

def test_extract_plugin_meta_no_readme(tmp_path):
    plugin_dir = tmp_path / "my-plugin"
    plugin_dir.mkdir()
    meta = _extract_plugin_meta(plugin_dir)
    assert meta["name"] == "my-plugin"
    assert "source_url" not in meta
    assert "description" not in meta


def test_extract_plugin_meta_with_readme(tmp_path):
    plugin_dir = tmp_path / "cool-plugin"
    plugin_dir.mkdir()
    (plugin_dir / "README.md").write_text(
        "# Cool Plugin\n\nA useful tool for coding.\n\n"
        "Source: https://github.com/user/cool-plugin\n"
    )
    meta = _extract_plugin_meta(plugin_dir)
    assert meta["name"] == "cool-plugin"
    assert meta["source_url"] == "https://github.com/user/cool-plugin"
    assert meta["description"] == "Cool Plugin"


def test_extract_plugin_meta_no_github_url(tmp_path):
    plugin_dir = tmp_path / "local-plugin"
    plugin_dir.mkdir()
    (plugin_dir / "README.md").write_text("# Local Plugin\n\nNo external source.")
    meta = _extract_plugin_meta(plugin_dir)
    assert meta["name"] == "local-plugin"
    assert "source_url" not in meta
    assert meta["description"] == "Local Plugin"


def test_collect_all_skills_plugins_include_meta(tmp_path, monkeypatch):
    claude_dir = tmp_path / "claude"
    claude_dir.mkdir()
    plugin_dir = claude_dir / "plugins" / "marketplaces" / "official" / "plugins" / "test-plugin"
    commands_dir = plugin_dir / "commands"
    commands_dir.mkdir(parents=True)
    (commands_dir / "do-thing.md").write_text("Skill content")
    (plugin_dir / "README.md").write_text(
        "# Test Plugin\n\nDoes things.\nhttps://github.com/user/test-plugin\n"
    )
    monkeypatch.setattr("claude_dashboard.data.CLAUDE_DIR", claude_dir)
    monkeypatch.setattr("claude_dashboard.data.PROJECTS_DIR", tmp_path / "projects")
    result = collect_all_skills()
    plugin = result["plugins"][0]
    assert plugin["name"] == "test-plugin"
    assert plugin["marketplace"] == "official"
    assert plugin["source_url"] == "https://github.com/user/test-plugin"
    assert plugin["description"] == "Test Plugin"
