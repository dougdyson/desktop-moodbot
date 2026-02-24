import argparse
import sys

from parsers.claude_code import ClaudeCodeParser
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
    args = parser.parse_args()

    monitors = [
        AgentMonitor("claude-code", ClaudeCodeParser()),
    ]

    watcher = WatcherLoop(monitors, interval=args.interval)
    set_watcher(watcher)

    watcher.start()
    print(f"Moodbot server starting on {args.host}:{args.port}")
    print(f"Agents: {', '.join(watcher.agent_names)}")
    print(f"Poll interval: {args.interval}s")
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
