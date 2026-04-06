import argparse
import os
import sys
from pathlib import Path

from core.state import MoodEngine
from parsers.claude_code import ClaudeCodeParser
from parsers.opencode import OpenCodeParser
from watcher.monitor import AgentMonitor, WatcherLoop
from server.app import run_server, set_watcher


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="moodbot",
        description="Desktop Mood Bot — AI agent mood display server",
    )
    parser.add_argument(
        "--port", type=int, default=9400, help="HTTP server port (default: 9400)"
    )
    parser.add_argument(
        "--host", type=str, default="0.0.0.0", help="HTTP server host (default: 0.0.0.0)"
    )
    parser.add_argument(
        "--interval", type=float, default=10.0, help="File poll interval in seconds (default: 10)"
    )
    parser.add_argument(
        "--no-sleep", action="store_true", help="Never return sleeping=true (for battery testing)"
    )
    args = parser.parse_args()

    sleep_timeout = float("inf") if args.no_sleep else None
    engine_kwargs = {"sleep_timeout": sleep_timeout} if sleep_timeout else {}

    claude_path = os.environ.get("CLAUDE_PROJECTS_PATH")
    claude_base = Path(claude_path) if claude_path else None

    opencode_db = os.environ.get("OPENCODE_DB_PATH")
    opencode_db_path = Path(opencode_db) if opencode_db else None

    monitors = [
        AgentMonitor("claude-code", ClaudeCodeParser(base_path=claude_base), engine=MoodEngine(**engine_kwargs)),
        AgentMonitor("opencode", OpenCodeParser(db_path=opencode_db_path), engine=MoodEngine(**engine_kwargs)),
    ]

    watcher = WatcherLoop(monitors, interval=args.interval)
    set_watcher(watcher)

    watcher.start()
    print(f"Moodbot server starting on {args.host}:{args.port}")
    print(f"Agents: {', '.join(watcher.agent_names)}")
    print(f"Poll interval: {args.interval}s")
    if args.no_sleep:
        print("Sleep disabled (battery test mode)")
    print(f"Try: curl http://localhost:{args.port}/mood/claude-code")

    server = run_server(host=args.host, port=args.port)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down...")
        watcher.stop()
        server.shutdown()


if __name__ == "__main__":
    main()
