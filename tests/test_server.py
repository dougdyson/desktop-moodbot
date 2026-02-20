import json
import threading
import time
from datetime import datetime, timezone
from pathlib import Path

import pytest

from parsers.claude_code import ClaudeCodeParser
from watcher.monitor import AgentMonitor, WatcherLoop
from server.app import MoodHandler, run_server, set_watcher

try:
    from urllib.request import urlopen, Request
    from urllib.error import HTTPError
except ImportError:
    pass


def _write_jsonl(tmp_path):
    project_dir = tmp_path / "proj"
    project_dir.mkdir(parents=True, exist_ok=True)
    path = project_dir / "session.jsonl"
    entry = json.dumps({
        "type": "assistant",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "message": {
            "role": "assistant",
            "content": [{"type": "text", "text": "This is a wonderful and helpful response"}],
        },
    })
    path.write_text(entry + "\n")
    return path


def _get(url: str) -> tuple[int, dict]:
    try:
        resp = urlopen(Request(url))
        return resp.status, json.loads(resp.read())
    except HTTPError as e:
        return e.code, json.loads(e.read())


@pytest.fixture
def live_server(tmp_path):
    _write_jsonl(tmp_path)
    parser = ClaudeCodeParser(base_path=tmp_path)
    monitor = AgentMonitor("claude-code", parser)
    watcher = WatcherLoop([monitor], interval=60)
    watcher.poll_all()
    set_watcher(watcher)

    server = run_server(host="127.0.0.1", port=0)
    port = server.server_address[1]
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()

    yield f"http://127.0.0.1:{port}"

    server.shutdown()


class TestMoodEndpoint:
    def test_returns_mood_json(self, live_server):
        status, data = _get(f"{live_server}/mood/claude-code")
        assert status == 200
        assert "activity" in data
        assert "emotion" in data
        assert "variant" in data
        assert "sleeping" in data
        assert "bitmap" in data

    def test_unknown_agent_returns_404(self, live_server):
        status, data = _get(f"{live_server}/mood/nonexistent")
        assert status == 404
        assert "error" in data


class TestAgentsListEndpoint:
    def test_returns_all_agents(self, live_server):
        status, data = _get(f"{live_server}/mood")
        assert status == 200
        assert "agents" in data
        assert "claude-code" in data["agents"]


class TestHealthEndpoint:
    def test_returns_ok(self, live_server):
        status, data = _get(f"{live_server}/health")
        assert status == 200
        assert data["status"] == "ok"


class TestFirmwareEndpoint:
    def test_returns_version(self, live_server):
        status, data = _get(f"{live_server}/firmware/latest")
        assert status == 200
        assert "version" in data


class TestNotFound:
    def test_unknown_path(self, live_server):
        status, data = _get(f"{live_server}/nonexistent")
        assert status == 404
