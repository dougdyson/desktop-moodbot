import json
import sqlite3
import time
from datetime import datetime, timezone
from pathlib import Path

import pytest

from parsers.base import Activity, ParsedMessage, ParsedSession
from parsers.opencode import OpenCodeParser

TS_BASE = 1775500780000


def _init_db(db_path: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(str(db_path))
    conn.execute("""
        CREATE TABLE project (
            id TEXT PRIMARY KEY,
            path TEXT NOT NULL,
            time_created INTEGER NOT NULL,
            time_updated INTEGER NOT NULL
        )
    """)
    conn.execute("""
        CREATE TABLE session (
            id TEXT PRIMARY KEY,
            project_id TEXT NOT NULL,
            parent_id TEXT,
            slug TEXT NOT NULL,
            directory TEXT NOT NULL,
            title TEXT NOT NULL,
            version TEXT NOT NULL,
            time_created INTEGER NOT NULL,
            time_updated INTEGER NOT NULL,
            time_compacting INTEGER,
            time_archived INTEGER,
            share_url TEXT,
            summary_additions INTEGER,
            summary_deletions INTEGER,
            summary_files INTEGER,
            summary_diffs TEXT,
            revert TEXT,
            permission TEXT,
            workspace_id TEXT,
            FOREIGN KEY (project_id) REFERENCES project(id)
        )
    """)
    conn.execute("""
        CREATE TABLE message (
            id TEXT PRIMARY KEY,
            session_id TEXT NOT NULL,
            time_created INTEGER NOT NULL,
            time_updated INTEGER NOT NULL,
            data TEXT NOT NULL,
            FOREIGN KEY (session_id) REFERENCES session(id)
        )
    """)
    conn.execute("""
        CREATE TABLE part (
            id TEXT PRIMARY KEY,
            message_id TEXT NOT NULL,
            session_id TEXT NOT NULL,
            time_created INTEGER NOT NULL,
            time_updated INTEGER NOT NULL,
            data TEXT NOT NULL,
            FOREIGN KEY (message_id) REFERENCES message(id)
        )
    """)
    conn.execute(
        "INSERT INTO project VALUES (?, ?, ?, ?)",
        ("proj1", "/tmp/test-project", TS_BASE, TS_BASE),
    )
    conn.commit()
    return conn


def _add_session(conn, session_id="ses_1", title="Test Session", ts=TS_BASE):
    conn.execute(
        "INSERT INTO session VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (session_id, "proj1", None, "test", "/tmp/test-project", title, "1.0",
         ts, ts, None, None, None, None, None, None, None, None, None, None),
    )
    conn.commit()


def _add_message(conn, msg_id, session_id, role="assistant", ts=TS_BASE, **extra):
    data = {"role": role, "time": {"created": ts}}
    if role == "assistant":
        data.update({
            "modelID": "test-model",
            "providerID": "test",
            "cost": 0,
            "tokens": {"total": 100, "input": 50, "output": 50, "reasoning": 0, "cache": {"write": 0, "read": 0}},
        })
    data.update(extra)
    conn.execute(
        "INSERT INTO message VALUES (?, ?, ?, ?, ?)",
        (msg_id, session_id, ts, ts, json.dumps(data)),
    )
    conn.commit()


def _add_part(conn, part_id, msg_id, session_id, part_type, ts=TS_BASE, **extra):
    data = {"type": part_type, **extra}
    conn.execute(
        "INSERT INTO part VALUES (?, ?, ?, ?, ?, ?)",
        (part_id, msg_id, session_id, ts, ts, json.dumps(data)),
    )
    conn.commit()


class TestSessionDiscovery:
    def test_discover_finds_sessions(self, tmp_path):
        db_path = tmp_path / "opencode.db"
        conn = _init_db(db_path)
        _add_session(conn, "ses_1", ts=TS_BASE)
        _add_session(conn, "ses_2", ts=TS_BASE + 1000)
        conn.close()

        parser = OpenCodeParser(db_path=db_path)
        sessions = parser.discover_sessions()
        assert len(sessions) == 2

    def test_discover_returns_empty_for_missing_db(self, tmp_path):
        parser = OpenCodeParser(db_path=tmp_path / "nonexistent.db")
        assert parser.discover_sessions() == []

    def test_find_active_session_returns_db_path(self, tmp_path):
        db_path = tmp_path / "opencode.db"
        conn = _init_db(db_path)
        _add_session(conn, "ses_old", ts=TS_BASE)
        _add_session(conn, "ses_new", ts=TS_BASE + 60000)
        conn.close()

        parser = OpenCodeParser(db_path=db_path)
        active = parser.find_active_session()
        assert active == db_path

    def test_find_active_session_returns_none_when_empty(self, tmp_path):
        db_path = tmp_path / "opencode.db"
        conn = _init_db(db_path)
        conn.close()

        parser = OpenCodeParser(db_path=db_path)
        assert parser.find_active_session() is None

    def test_find_active_session_returns_none_for_missing_db(self, tmp_path):
        parser = OpenCodeParser(db_path=tmp_path / "nonexistent.db")
        assert parser.find_active_session() is None


class TestEntryParsing:
    def test_parses_text_message(self, tmp_path):
        db_path = tmp_path / "opencode.db"
        conn = _init_db(db_path)
        _add_session(conn, "ses_1")
        _add_message(conn, "msg_1", "ses_1")
        _add_part(conn, "prt_1", "msg_1", "ses_1", "text",
                  text="This is a helpful response to your question")
        conn.close()

        parser = OpenCodeParser(db_path=db_path)
        session = parser.parse_session(Path("ses_1"))
        assert len(session.messages) == 1
        assert session.messages[0].text == "This is a helpful response to your question"
        assert session.messages[0].activity == Activity.CONVERSING

    def test_parses_reasoning_only(self, tmp_path):
        db_path = tmp_path / "opencode.db"
        conn = _init_db(db_path)
        _add_session(conn, "ses_1")
        _add_message(conn, "msg_1", "ses_1")
        _add_part(conn, "prt_1", "msg_1", "ses_1", "reasoning",
                  text="Let me analyze this problem")
        conn.close()

        parser = OpenCodeParser(db_path=db_path)
        session = parser.parse_session(Path("ses_1"))
        assert len(session.messages) == 1
        assert session.messages[0].activity == Activity.THINKING

    def test_parses_user_entries(self, tmp_path):
        db_path = tmp_path / "opencode.db"
        conn = _init_db(db_path)
        _add_session(conn, "ses_1")
        _add_message(conn, "msg_1", "ses_1", role="user", ts=TS_BASE)
        _add_part(conn, "prt_1", "msg_1", "ses_1", "text", ts=TS_BASE,
                  text="Thanks, that works perfectly for my use case")
        _add_message(conn, "msg_2", "ses_1", role="assistant", ts=TS_BASE + 1000)
        _add_part(conn, "prt_2", "msg_2", "ses_1", "text", ts=TS_BASE + 1000,
                  text="This is a valid response with enough text")
        conn.close()

        parser = OpenCodeParser(db_path=db_path)
        session = parser.parse_session(Path("ses_1"))
        assert len(session.messages) == 2
        assert session.messages[0].role == "user"
        assert session.messages[1].role == "assistant"

    def test_skips_short_user_entries(self, tmp_path):
        db_path = tmp_path / "opencode.db"
        conn = _init_db(db_path)
        _add_session(conn, "ses_1")
        _add_message(conn, "msg_1", "ses_1", role="user", ts=TS_BASE)
        _add_part(conn, "prt_1", "msg_1", "ses_1", "text", ts=TS_BASE, text="Hello")
        _add_message(conn, "msg_2", "ses_1", role="assistant", ts=TS_BASE + 1000)
        _add_part(conn, "prt_2", "msg_2", "ses_1", "text", ts=TS_BASE + 1000,
                  text="This is a valid response with enough text")
        conn.close()

        parser = OpenCodeParser(db_path=db_path)
        session = parser.parse_session(Path("ses_1"))
        assert len(session.messages) == 1
        assert session.messages[0].role == "assistant"

    def test_parses_timestamp(self, tmp_path):
        db_path = tmp_path / "opencode.db"
        conn = _init_db(db_path)
        _add_session(conn, "ses_1")
        _add_message(conn, "msg_1", "ses_1", ts=1775500845123)
        _add_part(conn, "prt_1", "msg_1", "ses_1", "text", ts=1775500845123,
                  text="A response with enough characters to pass the filter")
        conn.close()

        parser = OpenCodeParser(db_path=db_path)
        session = parser.parse_session(Path("ses_1"))
        assert session.messages[0].timestamp.tzinfo is not None


class TestActivityClassification:
    @pytest.mark.parametrize("tool,expected", [
        ("read", Activity.READING),
        ("grep", Activity.READING),
        ("glob", Activity.READING),
        ("ls", Activity.READING),
        ("codesearch", Activity.READING),
        ("websearch", Activity.READING),
        ("webfetch", Activity.READING),
        ("edit", Activity.EDITING),
        ("write", Activity.EDITING),
        ("multiedit", Activity.EDITING),
        ("apply_patch", Activity.EDITING),
        ("plan", Activity.SYSTEM),
        ("task", Activity.SYSTEM),
        ("todo", Activity.SYSTEM),
        ("skill", Activity.SYSTEM),
        ("batch", Activity.SYSTEM),
        ("question", Activity.SYSTEM),
    ])
    def test_tool_to_activity_mapping(self, tool, expected, tmp_path):
        db_path = tmp_path / "opencode.db"
        conn = _init_db(db_path)
        _add_session(conn, "ses_1")
        _add_message(conn, "msg_1", "ses_1")
        _add_part(conn, "prt_1", "msg_1", "ses_1", "tool",
                  tool=tool, callID="call_1",
                  state={"status": "completed", "input": {}, "output": ""})
        conn.close()

        parser = OpenCodeParser(db_path=db_path)
        session = parser.parse_session(Path("ses_1"))
        assert len(session.messages) == 1
        assert session.messages[0].activity == expected

    def test_bash_default_is_executing(self, tmp_path):
        db_path = tmp_path / "opencode.db"
        conn = _init_db(db_path)
        _add_session(conn, "ses_1")
        _add_message(conn, "msg_1", "ses_1")
        _add_part(conn, "prt_1", "msg_1", "ses_1", "tool",
                  tool="bash", callID="call_1",
                  state={"status": "completed", "input": {"command": "ls -la /tmp"}, "output": ""})
        conn.close()

        parser = OpenCodeParser(db_path=db_path)
        session = parser.parse_session(Path("ses_1"))
        assert session.messages[0].activity == Activity.EXECUTING

    def test_bash_git_commit_is_system(self, tmp_path):
        db_path = tmp_path / "opencode.db"
        conn = _init_db(db_path)
        _add_session(conn, "ses_1")
        _add_message(conn, "msg_1", "ses_1")
        _add_part(conn, "prt_1", "msg_1", "ses_1", "tool",
                  tool="bash", callID="call_1",
                  state={"status": "completed", "input": {"command": "git commit -m 'test'"}, "output": ""})
        conn.close()

        parser = OpenCodeParser(db_path=db_path)
        session = parser.parse_session(Path("ses_1"))
        assert session.messages[0].activity == Activity.SYSTEM

    def test_bash_pytest_is_executing(self, tmp_path):
        db_path = tmp_path / "opencode.db"
        conn = _init_db(db_path)
        _add_session(conn, "ses_1")
        _add_message(conn, "msg_1", "ses_1")
        _add_part(conn, "prt_1", "msg_1", "ses_1", "tool",
                  tool="bash", callID="call_1",
                  state={"status": "completed", "input": {"command": "python -m pytest tests/ -v"}, "output": ""})
        conn.close()

        parser = OpenCodeParser(db_path=db_path)
        session = parser.parse_session(Path("ses_1"))
        assert session.messages[0].activity == Activity.EXECUTING


class TestToolErrors:
    def test_tool_error_detected(self, tmp_path):
        db_path = tmp_path / "opencode.db"
        conn = _init_db(db_path)
        _add_session(conn, "ses_1")
        _add_message(conn, "msg_1", "ses_1")
        _add_part(conn, "prt_1", "msg_1", "ses_1", "tool",
                  tool="bash", callID="call_1",
                  state={"status": "error", "input": {"command": "npm test"}, "error": "tests failed"})
        _add_part(conn, "prt_2", "msg_1", "ses_1", "text",
                  text="The tests failed, let me investigate the issue")
        conn.close()

        parser = OpenCodeParser(db_path=db_path)
        session = parser.parse_session(Path("ses_1"))
        error_msgs = [m for m in session.messages if m.is_error]
        assert len(error_msgs) == 1
        assert error_msgs[0].role == "tool_result"


class TestNoiseFiltering:
    def test_filters_short_messages(self, tmp_path):
        db_path = tmp_path / "opencode.db"
        conn = _init_db(db_path)
        _add_session(conn, "ses_1")
        _add_message(conn, "msg_1", "ses_1")
        _add_part(conn, "prt_1", "msg_1", "ses_1", "text", text="OK")
        conn.close()

        parser = OpenCodeParser(db_path=db_path)
        session = parser.parse_session(Path("ses_1"))
        assert len(session.messages) == 0

    def test_truncates_long_messages(self, tmp_path):
        db_path = tmp_path / "opencode.db"
        conn = _init_db(db_path)
        _add_session(conn, "ses_1")
        _add_message(conn, "msg_1", "ses_1")
        _add_part(conn, "prt_1", "msg_1", "ses_1", "text", text="A" * 2000)
        conn.close()

        parser = OpenCodeParser(db_path=db_path)
        session = parser.parse_session(Path("ses_1"))
        assert len(session.messages[0].text) == 1500


class TestLastN:
    def test_respects_last_n_limit(self, tmp_path):
        db_path = tmp_path / "opencode.db"
        conn = _init_db(db_path)
        _add_session(conn, "ses_1")
        for i in range(20):
            ts = TS_BASE + i * 1000
            _add_message(conn, f"msg_{i}", "ses_1", ts=ts)
            _add_part(conn, f"prt_{i}", f"msg_{i}", "ses_1", "text", ts=ts,
                      text=f"Message number {i} with enough text to pass the filter")
        conn.close()

        parser = OpenCodeParser(db_path=db_path)
        session = parser.parse_session(Path("ses_1"), last_n=5)
        assert len(session.messages) == 5
        assert "15" in session.messages[0].text

    def test_returns_all_when_fewer_than_n(self, tmp_path):
        db_path = tmp_path / "opencode.db"
        conn = _init_db(db_path)
        _add_session(conn, "ses_1")
        _add_message(conn, "msg_1", "ses_1")
        _add_part(conn, "prt_1", "msg_1", "ses_1", "text",
                  text="Only message with enough characters to pass filtering")
        conn.close()

        parser = OpenCodeParser(db_path=db_path)
        session = parser.parse_session(Path("ses_1"), last_n=100)
        assert len(session.messages) == 1


class TestParsedSession:
    def test_last_activity_time(self, tmp_path):
        db_path = tmp_path / "opencode.db"
        conn = _init_db(db_path)
        _add_session(conn, "ses_1")
        _add_message(conn, "msg_1", "ses_1", ts=TS_BASE)
        _add_part(conn, "prt_1", "msg_1", "ses_1", "text", ts=TS_BASE,
                  text="First message with enough characters here")
        _add_message(conn, "msg_2", "ses_1", ts=TS_BASE + 300000)
        _add_part(conn, "prt_2", "msg_2", "ses_1", "text", ts=TS_BASE + 300000,
                  text="Second message with enough characters here")
        conn.close()

        parser = OpenCodeParser(db_path=db_path)
        session = parser.parse_session(Path("ses_1"))
        assert session.last_activity_time is not None
        assert session.last_activity_time > session.messages[0].timestamp

    def test_tracks_session_mtime(self, tmp_path):
        db_path = tmp_path / "opencode.db"
        conn = _init_db(db_path)
        _add_session(conn, "ses_1", ts=TS_BASE)
        _add_message(conn, "msg_1", "ses_1")
        _add_part(conn, "prt_1", "msg_1", "ses_1", "text",
                  text="A message with enough text to pass filtering")
        conn.close()

        parser = OpenCodeParser(db_path=db_path)
        session = parser.parse_session(Path("ses_1"))
        assert session.last_modified is not None


class TestEdgeCases:
    def test_empty_session(self, tmp_path):
        db_path = tmp_path / "opencode.db"
        conn = _init_db(db_path)
        _add_session(conn, "ses_1")
        conn.close()

        parser = OpenCodeParser(db_path=db_path)
        session = parser.parse_session(Path("ses_1"))
        assert len(session.messages) == 0

    def test_missing_db(self, tmp_path):
        parser = OpenCodeParser(db_path=tmp_path / "nonexistent.db")
        session = parser.parse_session(Path("ses_1"))
        assert len(session.messages) == 0

    def test_step_parts_ignored(self, tmp_path):
        db_path = tmp_path / "opencode.db"
        conn = _init_db(db_path)
        _add_session(conn, "ses_1")
        _add_message(conn, "msg_1", "ses_1")
        _add_part(conn, "prt_1", "msg_1", "ses_1", "step-start",
                  snapshot="abc123")
        _add_part(conn, "prt_2", "msg_1", "ses_1", "text",
                  text="Here is my analysis of the codebase structure")
        _add_part(conn, "prt_3", "msg_1", "ses_1", "step-finish",
                  reason="stop", cost=0)
        conn.close()

        parser = OpenCodeParser(db_path=db_path)
        session = parser.parse_session(Path("ses_1"))
        assert len(session.messages) == 1
        assert session.messages[0].activity == Activity.CONVERSING

    def test_multiple_text_parts_combined(self, tmp_path):
        db_path = tmp_path / "opencode.db"
        conn = _init_db(db_path)
        _add_session(conn, "ses_1")
        _add_message(conn, "msg_1", "ses_1")
        _add_part(conn, "prt_1", "msg_1", "ses_1", "text",
                  text="First part of the response")
        _add_part(conn, "prt_2", "msg_1", "ses_1", "text",
                  text="Second part of the response")
        conn.close()

        parser = OpenCodeParser(db_path=db_path)
        session = parser.parse_session(Path("ses_1"))
        assert len(session.messages) == 1
        assert "First part" in session.messages[0].text
        assert "Second part" in session.messages[0].text


class TestRealDataFormat:
    def test_parses_realistic_session(self, tmp_path):
        db_path = tmp_path / "opencode.db"
        conn = _init_db(db_path)
        _add_session(conn, "ses_1")

        _add_message(conn, "msg_user", "ses_1", role="user", ts=TS_BASE)
        _add_part(conn, "prt_u1", "msg_user", "ses_1", "text", ts=TS_BASE,
                  text="What files are in this project? Give me a brief summary")

        _add_message(conn, "msg_a1", "ses_1", role="assistant", ts=TS_BASE + 1000)
        _add_part(conn, "prt_a1", "msg_a1", "ses_1", "step-start", ts=TS_BASE + 1000,
                  snapshot="abc123")
        _add_part(conn, "prt_a2", "msg_a1", "ses_1", "reasoning", ts=TS_BASE + 1100,
                  text="Let me explore the directory structure")
        _add_part(conn, "prt_a3", "msg_a1", "ses_1", "tool", ts=TS_BASE + 1200,
                  tool="glob", callID="call_1",
                  state={"status": "completed", "input": {"pattern": "**/*"}, "output": "..."})
        _add_part(conn, "prt_a4", "msg_a1", "ses_1", "tool", ts=TS_BASE + 1300,
                  tool="read", callID="call_2",
                  state={"status": "completed", "input": {"filePath": "/tmp/README.md"}, "output": "..."})
        _add_part(conn, "prt_a5", "msg_a1", "ses_1", "step-finish", ts=TS_BASE + 1400,
                  reason="tool-calls", cost=0)

        _add_message(conn, "msg_a2", "ses_1", role="assistant", ts=TS_BASE + 2000)
        _add_part(conn, "prt_b1", "msg_a2", "ses_1", "step-start", ts=TS_BASE + 2000,
                  snapshot="abc123")
        _add_part(conn, "prt_b2", "msg_a2", "ses_1", "text", ts=TS_BASE + 2100,
                  text="Desktop Mood Bot is a Python service that reads AI coding agent logs and computes mood state.")
        _add_part(conn, "prt_b3", "msg_a2", "ses_1", "step-finish", ts=TS_BASE + 2200,
                  reason="stop", cost=0)
        conn.close()

        parser = OpenCodeParser(db_path=db_path)
        session = parser.parse_session(Path("ses_1"))

        assert len(session.messages) == 3
        assert session.messages[0].role == "user"
        assert session.messages[0].activity == Activity.CONVERSING

        assert session.messages[1].activity == Activity.READING
        assert session.messages[1].tool_name == "read"

        assert session.messages[2].activity == Activity.CONVERSING
        assert "Desktop Mood Bot" in session.messages[2].text
