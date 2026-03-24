import json
import textwrap
from pathlib import Path

from claude_dashboard.server import (
    extract_memory_files,
    extract_sessions,
    format_date,
    get_dir_fingerprint,
    get_html,
    project_display_name,
)


def test_project_display_name_with_subpath():
    assert project_display_name("-Users-jwong-ws-jira") == "~/ws/jira"


def test_project_display_name_home():
    assert project_display_name("-Users-jwong") == "~"


def test_project_display_name_deep_path():
    assert project_display_name("-Users-jwong-ws-some-project") == "~/ws/some/project"


def test_project_display_name_unknown_user():
    assert project_display_name("-Users-other-stuff") == "-Users-other-stuff"


def test_format_date_iso():
    assert format_date("2026-03-05T22:52:10.332Z") == "2026-03-05 22:52"


def test_format_date_empty():
    assert format_date("") == ""
    assert format_date(None) == ""


def test_format_date_malformed():
    result = format_date("not-a-date")
    assert isinstance(result, str)


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


def test_get_html_returns_valid_html():
    html = get_html()
    assert "<!DOCTYPE html>" in html
    assert "Claude Code Dashboard" in html
    assert "/api/data" in html


def test_get_dir_fingerprint_returns_string(tmp_path, monkeypatch):
    monkeypatch.setattr("claude_dashboard.server.PROJECTS_DIR", tmp_path)
    fp = get_dir_fingerprint()
    assert isinstance(fp, str)
    assert len(fp) == 32  # md5 hex digest


def test_get_dir_fingerprint_changes_on_new_file(tmp_path, monkeypatch):
    monkeypatch.setattr("claude_dashboard.server.PROJECTS_DIR", tmp_path)
    project = tmp_path / "test-project"
    project.mkdir()

    fp1 = get_dir_fingerprint()
    (project / "session.jsonl").write_text("{}")
    fp2 = get_dir_fingerprint()
    assert fp1 != fp2


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
