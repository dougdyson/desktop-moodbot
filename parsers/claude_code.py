import json
import re
from datetime import datetime
from pathlib import Path
from typing import Optional

from .base import Activity, AgentParser, ParsedMessage, ParsedSession

TOOL_ACTIVITY_MAP = {
    "Read": Activity.READING,
    "Grep": Activity.READING,
    "Glob": Activity.READING,
    "WebSearch": Activity.READING,
    "WebFetch": Activity.READING,
    "Edit": Activity.EDITING,
    "Write": Activity.EDITING,
    "NotebookEdit": Activity.EDITING,
    "Bash": Activity.EXECUTING,
    "Task": Activity.SYSTEM,
    "TaskOutput": Activity.SYSTEM,
    "EnterPlanMode": Activity.SYSTEM,
    "ExitPlanMode": Activity.SYSTEM,
    "Skill": Activity.SYSTEM,
    "ToolSearch": Activity.SYSTEM,
}

BASH_GIT_PATTERNS = re.compile(
    r"\b(git\s+(commit|push|merge|rebase|cherry-pick|tag))\b"
)
BASH_TEST_PATTERNS = re.compile(
    r"\b(pytest|python\s+-m\s+pytest|npm\s+test|jest|mocha)\b"
)

TOOL_CALL_XML = re.compile(r"<(function_calls|invoke)\b")
TOOL_PREAMBLE = re.compile(
    r"^(let me |i'll |i will |running |checking |looking |reading |searching )",
    re.IGNORECASE,
)
TOOL_KEYWORDS = re.compile(
    r"\b(read|grep|glob|bash|search|file|edit|write|check|run)\b", re.IGNORECASE
)
SYSTEM_TAGS = re.compile(
    r"<(system-reminder|task-notification|user-prompt-submit-hook)[^>]*>.*?"
    r"</(system-reminder|task-notification|user-prompt-submit-hook)>",
    re.DOTALL,
)

MIN_MESSAGE_LENGTH = 20
MAX_MESSAGE_LENGTH = 1500


class ClaudeCodeParser(AgentParser):
    def __init__(self, base_path: Optional[Path] = None):
        self.base_path = base_path or Path.home() / ".claude" / "projects"

    def discover_sessions(self) -> list[Path]:
        if not self.base_path.exists():
            return []
        return sorted(self.base_path.glob("*/*.jsonl"))

    def parse_session(self, path: Path, last_n: int = 100) -> ParsedSession:
        session = ParsedSession(file_path=path)
        try:
            session.last_modified = path.stat().st_mtime
        except OSError:
            return session

        entries = self._read_tail(path, last_n * 3)
        messages = []
        for entry in entries:
            parsed = self._parse_entry(entry)
            if parsed:
                messages.append(parsed)

        session.messages = messages[-last_n:]
        return session

    def _read_tail(self, path: Path, max_lines: int) -> list[dict]:
        entries = []
        try:
            with open(path, "r", encoding="utf-8") as f:
                lines = f.readlines()
            for line in lines[-max_lines:]:
                line = line.strip()
                if not line:
                    continue
                try:
                    entries.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
        except (OSError, UnicodeDecodeError):
            pass
        return entries

    def _parse_entry(self, entry: dict) -> Optional[ParsedMessage]:
        if entry.get("type") != "assistant":
            return None

        timestamp = self._parse_timestamp(entry.get("timestamp"))
        if not timestamp:
            return None

        message = entry.get("message", {})
        content_blocks = message.get("content", [])
        if not isinstance(content_blocks, list):
            return None

        text_parts = []
        activity = Activity.THINKING
        tool_name = None

        for block in content_blocks:
            if not isinstance(block, dict):
                continue

            block_type = block.get("type")

            if block_type == "thinking":
                activity = Activity.THINKING

            elif block_type == "text":
                raw_text = block.get("text", "")
                cleaned = self._clean_text(raw_text)
                if cleaned and not self._is_tool_call_boilerplate(cleaned):
                    text_parts.append(cleaned)
                if activity == Activity.THINKING:
                    activity = Activity.CONVERSING

            elif block_type == "tool_use":
                name = block.get("name", "")
                tool_name = name
                activity = self._classify_tool(name, block.get("input", {}))

        text = " ".join(text_parts)
        if len(text) < MIN_MESSAGE_LENGTH and not tool_name:
            return None

        text = text[:MAX_MESSAGE_LENGTH]

        return ParsedMessage(
            timestamp=timestamp,
            text=text,
            activity=activity,
            tool_name=tool_name,
        )

    def _classify_tool(self, tool_name: str, tool_input: dict) -> Activity:
        if tool_name == "Bash":
            command = tool_input.get("command", "")
            if BASH_GIT_PATTERNS.search(command):
                return Activity.SYSTEM
            if BASH_TEST_PATTERNS.search(command):
                return Activity.EXECUTING
            return Activity.EXECUTING

        base_name = tool_name.split("__")[-1] if "__" in tool_name else tool_name
        return TOOL_ACTIVITY_MAP.get(base_name, Activity.SYSTEM)

    def _clean_text(self, text: str) -> str:
        text = SYSTEM_TAGS.sub("", text)
        return text.strip()

    def _is_tool_call_boilerplate(self, text: str) -> bool:
        if TOOL_CALL_XML.search(text):
            return True
        if len(text) < 80 and TOOL_PREAMBLE.match(text) and TOOL_KEYWORDS.search(text):
            return True
        return False

    def _parse_timestamp(self, ts: Optional[str]) -> Optional[datetime]:
        if not ts:
            return None
        try:
            ts = ts.replace("Z", "+00:00")
            return datetime.fromisoformat(ts)
        except (ValueError, TypeError):
            return None
