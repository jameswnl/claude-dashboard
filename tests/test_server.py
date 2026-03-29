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
    data_json, version = s.get()
    assert version == 1
    assert json.loads(data_json) == []

    # Create a project and refresh
    proj = tmp_path / (_home_prefix() + "-ws-x")
    proj.mkdir()
    d = {"type": "user", "message": {"role": "user", "content": "hi"},
         "timestamp": "2026-01-01T00:00:00Z", "sessionId": "s"}
    (proj / "s.jsonl").write_text(json.dumps(d))
    s.refresh()

    data_json, version = s.get()
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
