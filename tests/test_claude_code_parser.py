import json
import time
from datetime import datetime, timezone
from pathlib import Path

import pytest

from parsers.base import Activity, ParsedMessage, ParsedSession
from parsers.claude_code import ClaudeCodeParser


def _make_assistant_entry(
    text=None, tool_name=None, tool_input=None, thinking=None, timestamp=None
):
    ts = timestamp or "2026-02-20T14:30:00.000Z"
    blocks = []
    if thinking:
        blocks.append({"type": "thinking", "thinking": thinking})
    if text:
        blocks.append({"type": "text", "text": text})
    if tool_name:
        blocks.append({
            "type": "tool_use",
            "name": tool_name,
            "input": tool_input or {},
        })
    return json.dumps({
        "type": "assistant",
        "timestamp": ts,
        "message": {"role": "assistant", "content": blocks},
    })


def _make_user_entry(text="Hello", timestamp=None):
    ts = timestamp or "2026-02-20T14:29:00.000Z"
    return json.dumps({
        "type": "user",
        "timestamp": ts,
        "message": {"role": "user", "content": [{"type": "text", "text": text}]},
    })


def _make_system_entry(timestamp=None):
    ts = timestamp or "2026-02-20T14:28:00.000Z"
    return json.dumps({"type": "system", "timestamp": ts})


def _write_session(tmp_path, lines, project="test-project", name="session1.jsonl"):
    project_dir = tmp_path / project
    project_dir.mkdir(parents=True, exist_ok=True)
    path = project_dir / name
    path.write_text("\n".join(lines) + "\n")
    return path


class TestSessionDiscovery:
    def test_discover_finds_jsonl_files(self, tmp_path):
        _write_session(tmp_path, [_make_user_entry()], "proj-a", "s1.jsonl")
        _write_session(tmp_path, [_make_user_entry()], "proj-b", "s2.jsonl")

        parser = ClaudeCodeParser(base_path=tmp_path)
        sessions = parser.discover_sessions()
        assert len(sessions) == 2

    def test_discover_returns_empty_for_missing_dir(self, tmp_path):
        parser = ClaudeCodeParser(base_path=tmp_path / "nonexistent")
        assert parser.discover_sessions() == []

    def test_discover_ignores_non_jsonl(self, tmp_path):
        _write_session(tmp_path, [_make_user_entry()], "proj", "s1.jsonl")
        project_dir = tmp_path / "proj"
        (project_dir / "notes.txt").write_text("not a session")

        parser = ClaudeCodeParser(base_path=tmp_path)
        sessions = parser.discover_sessions()
        assert len(sessions) == 1

    def test_find_active_session_returns_most_recent(self, tmp_path):
        old = _write_session(tmp_path, [_make_user_entry()], "proj", "old.jsonl")
        time.sleep(0.05)
        new = _write_session(tmp_path, [_make_user_entry()], "proj", "new.jsonl")

        parser = ClaudeCodeParser(base_path=tmp_path)
        active = parser.find_active_session()
        assert active == new

    def test_find_active_session_returns_none_when_empty(self, tmp_path):
        parser = ClaudeCodeParser(base_path=tmp_path / "nonexistent")
        assert parser.find_active_session() is None


class TestEntryParsing:
    def test_parses_text_message(self, tmp_path):
        lines = [_make_assistant_entry(text="This is a helpful response to your question")]
        path = _write_session(tmp_path, lines)

        parser = ClaudeCodeParser(base_path=tmp_path)
        session = parser.parse_session(path)

        assert len(session.messages) == 1
        assert session.messages[0].text == "This is a helpful response to your question"
        assert session.messages[0].activity == Activity.CONVERSING

    def test_parses_thinking_block(self, tmp_path):
        lines = [_make_assistant_entry(thinking="Let me analyze this problem carefully")]
        path = _write_session(tmp_path, lines)

        parser = ClaudeCodeParser(base_path=tmp_path)
        session = parser.parse_session(path)
        assert len(session.messages) == 0

    def test_thinking_with_text_is_conversing(self, tmp_path):
        lines = [_make_assistant_entry(
            thinking="Let me think about this",
            text="Here's what I found after analyzing the code",
        )]
        path = _write_session(tmp_path, lines)

        parser = ClaudeCodeParser(base_path=tmp_path)
        session = parser.parse_session(path)

        assert len(session.messages) == 1
        assert session.messages[0].activity == Activity.CONVERSING

    def test_parses_timestamp(self, tmp_path):
        lines = [_make_assistant_entry(
            text="A response with enough characters to pass the filter",
            timestamp="2026-02-20T14:30:45.123Z",
        )]
        path = _write_session(tmp_path, lines)

        parser = ClaudeCodeParser(base_path=tmp_path)
        session = parser.parse_session(path)

        assert session.messages[0].timestamp.hour == 14
        assert session.messages[0].timestamp.minute == 30
        assert session.messages[0].timestamp.second == 45

    def test_skips_user_entries(self, tmp_path):
        lines = [
            _make_user_entry("Hello there"),
            _make_assistant_entry(text="This is a valid response with enough text"),
        ]
        path = _write_session(tmp_path, lines)

        parser = ClaudeCodeParser(base_path=tmp_path)
        session = parser.parse_session(path)
        assert len(session.messages) == 1

    def test_skips_system_entries(self, tmp_path):
        lines = [
            _make_system_entry(),
            _make_assistant_entry(text="This is a valid response with enough text"),
        ]
        path = _write_session(tmp_path, lines)

        parser = ClaudeCodeParser(base_path=tmp_path)
        session = parser.parse_session(path)
        assert len(session.messages) == 1

    def test_skips_malformed_json(self, tmp_path):
        lines = [
            "this is not json",
            _make_assistant_entry(text="A valid message that should still be parsed"),
        ]
        path = _write_session(tmp_path, lines)

        parser = ClaudeCodeParser(base_path=tmp_path)
        session = parser.parse_session(path)
        assert len(session.messages) == 1


class TestActivityClassification:
    @pytest.mark.parametrize("tool,expected", [
        ("Read", Activity.READING),
        ("Grep", Activity.READING),
        ("Glob", Activity.READING),
        ("WebSearch", Activity.READING),
        ("WebFetch", Activity.READING),
        ("Edit", Activity.EDITING),
        ("Write", Activity.EDITING),
        ("NotebookEdit", Activity.EDITING),
        ("Task", Activity.SYSTEM),
        ("TaskOutput", Activity.SYSTEM),
        ("EnterPlanMode", Activity.SYSTEM),
        ("Skill", Activity.SYSTEM),
        ("ToolSearch", Activity.SYSTEM),
    ])
    def test_tool_to_activity_mapping(self, tool, expected, tmp_path):
        lines = [_make_assistant_entry(tool_name=tool)]
        path = _write_session(tmp_path, lines)

        parser = ClaudeCodeParser(base_path=tmp_path)
        session = parser.parse_session(path)

        assert len(session.messages) == 1
        assert session.messages[0].activity == expected

    def test_bash_default_is_executing(self, tmp_path):
        lines = [_make_assistant_entry(
            tool_name="Bash",
            tool_input={"command": "ls -la /tmp"},
        )]
        path = _write_session(tmp_path, lines)

        parser = ClaudeCodeParser(base_path=tmp_path)
        session = parser.parse_session(path)
        assert session.messages[0].activity == Activity.EXECUTING

    def test_bash_git_commit_is_system(self, tmp_path):
        lines = [_make_assistant_entry(
            tool_name="Bash",
            tool_input={"command": "git commit -m 'test'"},
        )]
        path = _write_session(tmp_path, lines)

        parser = ClaudeCodeParser(base_path=tmp_path)
        session = parser.parse_session(path)
        assert session.messages[0].activity == Activity.SYSTEM

    def test_bash_git_push_is_system(self, tmp_path):
        lines = [_make_assistant_entry(
            tool_name="Bash",
            tool_input={"command": "git push origin main"},
        )]
        path = _write_session(tmp_path, lines)

        parser = ClaudeCodeParser(base_path=tmp_path)
        session = parser.parse_session(path)
        assert session.messages[0].activity == Activity.SYSTEM

    def test_bash_pytest_is_executing(self, tmp_path):
        lines = [_make_assistant_entry(
            tool_name="Bash",
            tool_input={"command": "python -m pytest tests/ -v"},
        )]
        path = _write_session(tmp_path, lines)

        parser = ClaudeCodeParser(base_path=tmp_path)
        session = parser.parse_session(path)
        assert session.messages[0].activity == Activity.EXECUTING

    def test_mcp_tool_extracts_base_name(self, tmp_path):
        lines = [_make_assistant_entry(
            tool_name="mcp__todo-server__todo_add",
        )]
        path = _write_session(tmp_path, lines)

        parser = ClaudeCodeParser(base_path=tmp_path)
        session = parser.parse_session(path)
        assert session.messages[0].activity == Activity.SYSTEM


class TestNoiseFiltering:
    def test_filters_short_messages(self, tmp_path):
        lines = [_make_assistant_entry(text="OK")]
        path = _write_session(tmp_path, lines)

        parser = ClaudeCodeParser(base_path=tmp_path)
        session = parser.parse_session(path)
        assert len(session.messages) == 0

    def test_filters_function_call_xml(self, tmp_path):
        lines = [_make_assistant_entry(
            text='<function_calls><invoke name="Read"><parameter name="file_path">/tmp/test</parameter></invoke></function_calls>'
        )]
        path = _write_session(tmp_path, lines)

        parser = ClaudeCodeParser(base_path=tmp_path)
        session = parser.parse_session(path)
        assert len(session.messages) == 0

    def test_filters_tool_preamble(self, tmp_path):
        lines = [_make_assistant_entry(text="Let me read the file for you")]
        path = _write_session(tmp_path, lines)

        parser = ClaudeCodeParser(base_path=tmp_path)
        session = parser.parse_session(path)
        assert len(session.messages) == 0

    def test_keeps_longer_preamble_like_text(self, tmp_path):
        lines = [_make_assistant_entry(
            text="Let me explain what I found in detail. The issue is that the configuration file has a syntax error on line 42 which prevents the server from starting properly."
        )]
        path = _write_session(tmp_path, lines)

        parser = ClaudeCodeParser(base_path=tmp_path)
        session = parser.parse_session(path)
        assert len(session.messages) == 1

    def test_strips_system_reminder_tags(self, tmp_path):
        text_with_tags = (
            "Here is my analysis of the code.\n"
            "<system-reminder>You should use tools</system-reminder>\n"
            "The function needs refactoring."
        )
        lines = [_make_assistant_entry(text=text_with_tags)]
        path = _write_session(tmp_path, lines)

        parser = ClaudeCodeParser(base_path=tmp_path)
        session = parser.parse_session(path)

        assert len(session.messages) == 1
        assert "<system-reminder>" not in session.messages[0].text

    def test_truncates_long_messages(self, tmp_path):
        long_text = "A" * 2000
        lines = [_make_assistant_entry(text=long_text)]
        path = _write_session(tmp_path, lines)

        parser = ClaudeCodeParser(base_path=tmp_path)
        session = parser.parse_session(path)

        assert len(session.messages[0].text) == 1500


class TestLastN:
    def test_respects_last_n_limit(self, tmp_path):
        lines = [
            _make_assistant_entry(
                text=f"Message number {i} with enough text to pass the filter",
                timestamp=f"2026-02-20T14:{i:02d}:00.000Z",
            )
            for i in range(20)
        ]
        path = _write_session(tmp_path, lines)

        parser = ClaudeCodeParser(base_path=tmp_path)
        session = parser.parse_session(path, last_n=5)
        assert len(session.messages) == 5
        assert "15" in session.messages[0].text

    def test_returns_all_when_fewer_than_n(self, tmp_path):
        lines = [
            _make_assistant_entry(text="Only message with enough characters to pass filtering"),
        ]
        path = _write_session(tmp_path, lines)

        parser = ClaudeCodeParser(base_path=tmp_path)
        session = parser.parse_session(path, last_n=100)
        assert len(session.messages) == 1


class TestParsedSession:
    def test_last_activity_time(self, tmp_path):
        lines = [
            _make_assistant_entry(
                text="First message with enough characters here",
                timestamp="2026-02-20T14:00:00.000Z",
            ),
            _make_assistant_entry(
                text="Second message with enough characters here",
                timestamp="2026-02-20T14:05:00.000Z",
            ),
        ]
        path = _write_session(tmp_path, lines)

        parser = ClaudeCodeParser(base_path=tmp_path)
        session = parser.parse_session(path)
        assert session.last_activity_time.minute == 5

    def test_last_activity_time_none_when_empty(self):
        session = ParsedSession(file_path=Path("/tmp/empty.jsonl"))
        assert session.last_activity_time is None

    def test_tracks_file_path(self, tmp_path):
        path = _write_session(tmp_path, [_make_user_entry()])
        parser = ClaudeCodeParser(base_path=tmp_path)
        session = parser.parse_session(path)
        assert session.file_path == path


class TestEdgeCases:
    def test_empty_file(self, tmp_path):
        project_dir = tmp_path / "proj"
        project_dir.mkdir()
        path = project_dir / "empty.jsonl"
        path.write_text("")

        parser = ClaudeCodeParser(base_path=tmp_path)
        session = parser.parse_session(path)
        assert len(session.messages) == 0

    def test_missing_timestamp(self, tmp_path):
        entry = json.dumps({
            "type": "assistant",
            "message": {
                "role": "assistant",
                "content": [{"type": "text", "text": "No timestamp on this message at all"}],
            },
        })
        path = _write_session(tmp_path, [entry])

        parser = ClaudeCodeParser(base_path=tmp_path)
        session = parser.parse_session(path)
        assert len(session.messages) == 0

    def test_missing_content_blocks(self, tmp_path):
        entry = json.dumps({
            "type": "assistant",
            "timestamp": "2026-02-20T14:30:00.000Z",
            "message": {"role": "assistant"},
        })
        path = _write_session(tmp_path, [entry])

        parser = ClaudeCodeParser(base_path=tmp_path)
        session = parser.parse_session(path)
        assert len(session.messages) == 0

    def test_nonexistent_file(self, tmp_path):
        parser = ClaudeCodeParser(base_path=tmp_path)
        session = parser.parse_session(tmp_path / "nope.jsonl")
        assert len(session.messages) == 0

    def test_tool_use_only_entry_still_captured(self, tmp_path):
        lines = [_make_assistant_entry(tool_name="Read", tool_input={"file_path": "/tmp/test.py"})]
        path = _write_session(tmp_path, lines)

        parser = ClaudeCodeParser(base_path=tmp_path)
        session = parser.parse_session(path)

        assert len(session.messages) == 1
        assert session.messages[0].activity == Activity.READING
        assert session.messages[0].tool_name == "Read"
