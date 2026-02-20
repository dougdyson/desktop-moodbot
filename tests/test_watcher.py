import json
import time
from datetime import datetime, timezone
from pathlib import Path

import pytest

from core.state import MoodState
from parsers.claude_code import ClaudeCodeParser
from watcher.monitor import AgentMonitor, WatcherLoop


def _write_jsonl(tmp_path, text="This is a helpful and positive response", project="proj", name="s.jsonl"):
    project_dir = tmp_path / project
    project_dir.mkdir(parents=True, exist_ok=True)
    path = project_dir / name
    entry = json.dumps({
        "type": "assistant",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "message": {
            "role": "assistant",
            "content": [{"type": "text", "text": text}],
        },
    })
    path.write_text(entry + "\n")
    return path


class TestAgentMonitor:
    def test_poll_returns_mood(self, tmp_path):
        _write_jsonl(tmp_path)
        parser = ClaudeCodeParser(base_path=tmp_path)
        monitor = AgentMonitor("claude-code", parser)

        assert monitor.current_mood is None
        changed = monitor.poll()
        assert changed is True
        assert monitor.current_mood is not None
        assert isinstance(monitor.current_mood, MoodState)

    def test_poll_returns_false_when_unchanged(self, tmp_path):
        _write_jsonl(tmp_path)
        parser = ClaudeCodeParser(base_path=tmp_path)
        monitor = AgentMonitor("claude-code", parser)

        monitor.poll()
        changed = monitor.poll()
        assert changed is False

    def test_poll_detects_file_change(self, tmp_path):
        path = _write_jsonl(tmp_path)
        parser = ClaudeCodeParser(base_path=tmp_path)
        monitor = AgentMonitor("claude-code", parser)

        monitor.poll()
        time.sleep(0.05)

        with open(path, "a") as f:
            entry = json.dumps({
                "type": "assistant",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "message": {
                    "role": "assistant",
                    "content": [{"type": "text", "text": "Another message with enough content"}],
                },
            })
            f.write(entry + "\n")

        changed = monitor.poll()
        assert changed is True

    def test_poll_returns_false_when_no_sessions(self, tmp_path):
        parser = ClaudeCodeParser(base_path=tmp_path / "empty")
        monitor = AgentMonitor("test", parser)

        changed = monitor.poll()
        assert changed is False
        assert monitor.current_mood is None


class TestWatcherLoop:
    def test_get_mood_returns_none_for_unknown_agent(self, tmp_path):
        parser = ClaudeCodeParser(base_path=tmp_path)
        monitor = AgentMonitor("claude-code", parser)
        watcher = WatcherLoop([monitor])

        assert watcher.get_mood("nonexistent") is None

    def test_poll_all_updates_monitors(self, tmp_path):
        _write_jsonl(tmp_path)
        parser = ClaudeCodeParser(base_path=tmp_path)
        monitor = AgentMonitor("claude-code", parser)
        watcher = WatcherLoop([monitor])

        watcher.poll_all()
        mood = watcher.get_mood("claude-code")
        assert mood is not None

    def test_agent_names(self, tmp_path):
        parser = ClaudeCodeParser(base_path=tmp_path)
        monitors = [
            AgentMonitor("claude-code", parser),
            AgentMonitor("openclaw", parser),
        ]
        watcher = WatcherLoop(monitors)
        assert set(watcher.agent_names) == {"claude-code", "openclaw"}

    def test_start_and_stop(self, tmp_path):
        _write_jsonl(tmp_path)
        parser = ClaudeCodeParser(base_path=tmp_path)
        monitor = AgentMonitor("claude-code", parser)
        watcher = WatcherLoop([monitor], interval=0.1)

        watcher.start()
        time.sleep(0.2)
        assert watcher.get_mood("claude-code") is not None
        watcher.stop()
