import threading
import time
from typing import Optional

from core.state import MoodEngine, MoodState
from parsers.base import AgentParser


class AgentMonitor:
    def __init__(self, name: str, parser: AgentParser, engine: Optional[MoodEngine] = None):
        self.name = name
        self.parser = parser
        self.engine = engine or MoodEngine()
        self._current_mood: Optional[MoodState] = None
        self._last_mtime: Optional[float] = None
        self._last_path: Optional[str] = None

    @property
    def current_mood(self) -> Optional[MoodState]:
        return self._current_mood

    def poll(self) -> bool:
        active = self.parser.find_active_session()
        if not active:
            return False

        try:
            mtime = active.stat().st_mtime
        except OSError:
            return False

        file_changed = str(active) != self._last_path or mtime != self._last_mtime

        if not file_changed and self._current_mood is not None:
            if not self._current_mood.sleeping:
                session = self.parser.parse_session(active, last_n=100)
                if self.engine._is_sleeping(session):
                    self._current_mood = self.engine.compute(session)
            return False

        session = self.parser.parse_session(active, last_n=100)
        self._current_mood = self.engine.compute(session)
        self._last_mtime = mtime
        self._last_path = str(active)
        return file_changed


class WatcherLoop:
    def __init__(self, monitors: list[AgentMonitor], interval: float = 10.0):
        self.monitors = {m.name: m for m in monitors}
        self.interval = interval
        self._running = False
        self._thread: Optional[threading.Thread] = None

    def get_mood(self, agent: str) -> Optional[MoodState]:
        monitor = self.monitors.get(agent)
        if not monitor:
            return None
        return monitor.current_mood

    @property
    def agent_names(self) -> list[str]:
        return list(self.monitors.keys())

    def poll_all(self) -> None:
        for monitor in self.monitors.values():
            monitor.poll()

    def start(self) -> None:
        self._running = True
        self.poll_all()
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._running = False
        if self._thread:
            self._thread.join(timeout=self.interval + 1)

    def _loop(self) -> None:
        while self._running:
            time.sleep(self.interval)
            if self._running:
                self.poll_all()
