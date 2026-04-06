import json
import re
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from .base import Activity, AgentParser, ParsedMessage, ParsedSession

TOOL_ACTIVITY_MAP = {
    "read": Activity.READING,
    "grep": Activity.READING,
    "glob": Activity.READING,
    "ls": Activity.READING,
    "codesearch": Activity.READING,
    "websearch": Activity.READING,
    "webfetch": Activity.READING,
    "edit": Activity.EDITING,
    "write": Activity.EDITING,
    "multiedit": Activity.EDITING,
    "apply_patch": Activity.EDITING,
    "bash": Activity.EXECUTING,
    "plan": Activity.SYSTEM,
    "task": Activity.SYSTEM,
    "todo": Activity.SYSTEM,
    "skill": Activity.SYSTEM,
    "batch": Activity.SYSTEM,
    "question": Activity.SYSTEM,
}

BASH_GIT_PATTERNS = re.compile(
    r"\b(git\s+(commit|push|merge|rebase|cherry-pick|tag))\b"
)
BASH_TEST_PATTERNS = re.compile(
    r"\b(pytest|python\s+-m\s+pytest|npm\s+test|jest|mocha)\b"
)

MIN_MESSAGE_LENGTH = 20
MAX_MESSAGE_LENGTH = 1500

DB_NAME = "opencode.db"


class OpenCodeParser(AgentParser):
    def __init__(self, db_path: Optional[Path] = None):
        self.db_path = db_path or Path.home() / ".local" / "share" / "opencode" / DB_NAME

    def discover_sessions(self) -> list[Path]:
        if not self.db_path.exists():
            return []
        try:
            conn = sqlite3.connect(str(self.db_path))
            rows = conn.execute(
                "SELECT id FROM session ORDER BY time_created ASC"
            ).fetchall()
            conn.close()
            return [Path(row[0]) for row in rows]
        except sqlite3.Error:
            return []

    def find_active_session(self) -> Optional[Path]:
        if not self.db_path.exists():
            return None
        try:
            conn = sqlite3.connect(str(self.db_path))
            row = conn.execute(
                "SELECT id FROM session ORDER BY time_updated DESC LIMIT 1"
            ).fetchone()
            conn.close()
            if row:
                return self.db_path
            return None
        except sqlite3.Error:
            return None

    def _resolve_session_id(self, path: Path) -> Optional[str]:
        if path == self.db_path:
            try:
                conn = sqlite3.connect(str(self.db_path))
                row = conn.execute(
                    "SELECT id FROM session ORDER BY time_updated DESC LIMIT 1"
                ).fetchone()
                conn.close()
                return row[0] if row else None
            except sqlite3.Error:
                return None
        return str(path)

    def parse_session(self, path: Path, last_n: int = 100) -> ParsedSession:
        session_id = self._resolve_session_id(path)
        session = ParsedSession(file_path=path)

        if not session_id or not self.db_path.exists():
            return session

        try:
            conn = sqlite3.connect(str(self.db_path))
            session.last_modified = self._get_session_mtime(conn, session_id)

            parts = self._fetch_parts(conn, session_id)
            conn.close()
        except sqlite3.Error:
            return session

        messages = []
        current_msg_id = None
        current_role = None
        text_parts: list[str] = []
        activity = Activity.THINKING
        tool_name = None
        timestamp = None
        is_error = False
        has_reasoning = False

        for msg_id, msg_data_str, part_data_str, part_time in parts:
            if msg_id != current_msg_id:
                if current_msg_id is not None:
                    msg = self._build_message(
                        current_role, timestamp, text_parts, activity,
                        tool_name, is_error, has_reasoning,
                    )
                    if msg:
                        messages.append(msg)

                current_msg_id = msg_id
                text_parts = []
                activity = Activity.THINKING
                tool_name = None
                is_error = False
                has_reasoning = False

                try:
                    msg_data = json.loads(msg_data_str)
                except (json.JSONDecodeError, TypeError):
                    msg_data = {}
                current_role = msg_data.get("role", "assistant")
                timestamp = self._extract_timestamp(msg_data, part_time)

            try:
                part_data = json.loads(part_data_str)
            except (json.JSONDecodeError, TypeError):
                continue

            part_type = part_data.get("type")

            if part_type == "text":
                text = part_data.get("text", "").strip()
                if text:
                    text_parts.append(text)
                    if current_role == "assistant":
                        activity = Activity.CONVERSING

            elif part_type == "reasoning":
                has_reasoning = True

            elif part_type == "tool":
                name = part_data.get("tool", "")
                tool_name = name
                activity = self._classify_tool(name, part_data)
                state = part_data.get("state", {})
                if state.get("status") == "error":
                    is_error = True

        if current_msg_id is not None:
            msg = self._build_message(
                current_role, timestamp, text_parts, activity,
                tool_name, is_error, has_reasoning,
            )
            if msg:
                messages.append(msg)

        session.messages = messages[-last_n:]
        return session

    def _get_session_mtime(self, conn: sqlite3.Connection, session_id: str) -> Optional[float]:
        row = conn.execute(
            "SELECT time_updated FROM session WHERE id = ?", (session_id,)
        ).fetchone()
        if row and row[0]:
            return row[0] / 1000.0
        return None

    def _fetch_parts(self, conn: sqlite3.Connection, session_id: str) -> list[tuple]:
        return conn.execute(
            """
            SELECT m.id, m.data, p.data, p.time_created
            FROM part p
            JOIN message m ON p.message_id = m.id
            WHERE p.session_id = ?
            ORDER BY m.time_created ASC, p.id ASC
            """,
            (session_id,),
        ).fetchall()

    def _extract_timestamp(self, msg_data: dict, part_time: int) -> datetime:
        time_obj = msg_data.get("time", {})
        ts_ms = time_obj.get("created") or time_obj.get("completed") or part_time
        if ts_ms:
            return datetime.fromtimestamp(ts_ms / 1000.0, tz=timezone.utc)
        return datetime.now(tz=timezone.utc)

    def _build_message(
        self,
        role: Optional[str],
        timestamp: Optional[datetime],
        text_parts: list[str],
        activity: Activity,
        tool_name: Optional[str],
        is_error: bool,
        has_reasoning: bool,
    ) -> Optional[ParsedMessage]:
        if not timestamp:
            return None

        text = " ".join(text_parts)

        if role == "user":
            if len(text) < MIN_MESSAGE_LENGTH:
                return None
            return ParsedMessage(
                timestamp=timestamp,
                text=text[:MAX_MESSAGE_LENGTH],
                activity=Activity.CONVERSING,
                role="user",
            )

        if is_error and text:
            return ParsedMessage(
                timestamp=timestamp,
                text=text[:MAX_MESSAGE_LENGTH],
                activity=Activity.EXECUTING,
                tool_name=tool_name,
                role="tool_result",
                is_error=True,
            )

        if len(text) < MIN_MESSAGE_LENGTH and not tool_name:
            if not has_reasoning:
                return None
            return ParsedMessage(
                timestamp=timestamp,
                text="",
                activity=Activity.THINKING,
            )

        return ParsedMessage(
            timestamp=timestamp,
            text=text[:MAX_MESSAGE_LENGTH],
            activity=activity,
            tool_name=tool_name,
        )

    def _classify_tool(self, tool_name: str, part_data: dict) -> Activity:
        if tool_name == "bash":
            state = part_data.get("state", {})
            command = state.get("input", {}).get("command", "")
            if BASH_GIT_PATTERNS.search(command):
                return Activity.SYSTEM
            if BASH_TEST_PATTERNS.search(command):
                return Activity.EXECUTING
            return Activity.EXECUTING
        return TOOL_ACTIVITY_MAP.get(tool_name, Activity.SYSTEM)
