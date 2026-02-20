from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Optional


class Activity(Enum):
    THINKING = "thinking"
    CONVERSING = "conversing"
    READING = "reading"
    EXECUTING = "executing"
    EDITING = "editing"
    SYSTEM = "system"


@dataclass
class ParsedMessage:
    timestamp: datetime
    text: str
    activity: Activity
    tool_name: Optional[str] = None


@dataclass
class ParsedSession:
    file_path: Path
    messages: list[ParsedMessage] = field(default_factory=list)
    last_modified: Optional[float] = None

    @property
    def last_activity_time(self) -> Optional[datetime]:
        if self.messages:
            return self.messages[-1].timestamp
        return None


class AgentParser(ABC):
    @abstractmethod
    def discover_sessions(self) -> list[Path]:
        """Find all JSONL session files for this agent."""

    @abstractmethod
    def parse_session(self, path: Path, last_n: int = 100) -> ParsedSession:
        """Parse a session file, returning the last N messages."""

    def find_active_session(self) -> Optional[Path]:
        """Return the most recently modified session file."""
        sessions = self.discover_sessions()
        if not sessions:
            return None
        return max(sessions, key=lambda p: p.stat().st_mtime)
