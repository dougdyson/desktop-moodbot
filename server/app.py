import json
from http.server import HTTPServer, BaseHTTPRequestHandler
from typing import Optional

from watcher.monitor import WatcherLoop

_watcher: Optional[WatcherLoop] = None


def set_watcher(watcher: WatcherLoop) -> None:
    global _watcher
    _watcher = watcher


class MoodHandler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        path = self.path.rstrip("/")

        if path.startswith("/mood/"):
            agent = path[6:]
            self._handle_mood(agent)
        elif path == "/mood":
            self._handle_agents_list()
        elif path.startswith("/firmware/latest"):
            self._handle_firmware()
        elif path == "/health":
            self._respond_json({"status": "ok"})
        else:
            self._respond_error(404, "Not found")

    def _handle_mood(self, agent: str) -> None:
        if not _watcher:
            self._respond_error(503, "Watcher not initialized")
            return

        mood = _watcher.get_mood(agent)
        if mood is None:
            self._respond_error(404, f"Agent '{agent}' not found or no data yet")
            return

        self._respond_json(mood.to_dict())

    def _handle_agents_list(self) -> None:
        if not _watcher:
            self._respond_error(503, "Watcher not initialized")
            return

        agents = {}
        for name in _watcher.agent_names:
            mood = _watcher.get_mood(name)
            agents[name] = mood.to_dict() if mood else None

        self._respond_json({"agents": agents})

    def _handle_firmware(self) -> None:
        self._respond_json({"version": "0.1.0", "update_available": False})

    def _respond_json(self, data: dict) -> None:
        body = json.dumps(data).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _respond_error(self, code: int, message: str) -> None:
        body = json.dumps({"error": message}).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format, *args) -> None:
        pass


def run_server(host: str = "0.0.0.0", port: int = 8080) -> HTTPServer:
    server = HTTPServer((host, port), MoodHandler)
    return server
