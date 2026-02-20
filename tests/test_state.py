import json
from datetime import datetime, timezone, timedelta
from pathlib import Path

import pytest

from core.sentiment import EmotionBand
from core.state import MoodEngine, MoodState, VARIANT_COUNTS
from parsers.base import Activity, ParsedMessage, ParsedSession


def _make_session(
    messages=None, last_modified=None, minutes_ago=0
):
    now = datetime.now(timezone.utc)
    if messages is None:
        ts = now - timedelta(minutes=minutes_ago)
        messages = [
            ParsedMessage(
                timestamp=ts,
                text="This is a helpful response to your question",
                activity=Activity.CONVERSING,
            )
        ]
    return ParsedSession(
        file_path=Path("/tmp/test.jsonl"),
        messages=messages,
        last_modified=last_modified,
    )


class TestMoodState:
    def test_to_dict(self):
        state = MoodState(
            activity="thinking",
            emotion="positive",
            variant=2,
            timestamp="2026-02-20T14:30:00Z",
            sleeping=False,
        )
        d = state.to_dict()
        assert d["activity"] == "thinking"
        assert d["emotion"] == "positive"
        assert d["variant"] == 2
        assert d["sleeping"] is False
        assert d["bitmap"] is None

    def test_to_dict_is_json_serializable(self):
        state = MoodState(
            activity="reading",
            emotion="neutral",
            variant=0,
            timestamp="2026-02-20T14:30:00Z",
            sleeping=True,
        )
        result = json.dumps(state.to_dict())
        assert isinstance(result, str)


class TestMoodEngine:
    def test_compute_returns_mood_state(self):
        engine = MoodEngine()
        session = _make_session(minutes_ago=1)
        mood = engine.compute(session)
        assert isinstance(mood, MoodState)

    def test_activity_from_last_message(self):
        engine = MoodEngine()
        now = datetime.now(timezone.utc)
        messages = [
            ParsedMessage(timestamp=now, text="Reading the code", activity=Activity.CONVERSING),
            ParsedMessage(timestamp=now, text="", activity=Activity.READING),
            ParsedMessage(timestamp=now, text="", activity=Activity.EDITING),
        ]
        session = _make_session(messages=messages, minutes_ago=0)
        mood = engine.compute(session)
        assert mood.activity == "editing"

    def test_emotion_from_text_content(self):
        engine = MoodEngine()
        now = datetime.now(timezone.utc)
        messages = [
            ParsedMessage(
                timestamp=now,
                text="This is absolutely wonderful and amazing! I love it!",
                activity=Activity.CONVERSING,
            )
            for _ in range(15)
        ]
        session = _make_session(messages=messages)
        mood = engine.compute(session)
        assert mood.emotion in ("positive", "elated")

    def test_sleeping_when_inactive(self):
        engine = MoodEngine(sleep_timeout=1800)
        session = _make_session(minutes_ago=60)
        mood = engine.compute(session)
        assert mood.sleeping is True

    def test_awake_when_recent(self):
        engine = MoodEngine(sleep_timeout=1800)
        session = _make_session(minutes_ago=1)
        mood = engine.compute(session)
        assert mood.sleeping is False

    def test_sleeping_when_no_messages(self):
        engine = MoodEngine()
        session = ParsedSession(file_path=Path("/tmp/empty.jsonl"), messages=[])
        mood = engine.compute(session)
        assert mood.sleeping is True

    def test_variant_within_bounds(self):
        engine = MoodEngine()
        session = _make_session(minutes_ago=1)
        for _ in range(50):
            mood = engine.compute(session)
            band = EmotionBand(mood.emotion)
            max_variants = VARIANT_COUNTS.get(band, 1)
            assert 0 <= mood.variant < max_variants

    def test_variant_rotates_for_high_frequency_bands(self):
        engine = MoodEngine()
        now = datetime.now(timezone.utc)
        messages = [
            ParsedMessage(timestamp=now, text="Neutral technical response here", activity=Activity.THINKING)
            for _ in range(15)
        ]
        session = _make_session(messages=messages)

        variants_seen = set()
        for _ in range(20):
            mood = engine.compute(session)
            variants_seen.add(mood.variant)

        if VARIANT_COUNTS.get(EmotionBand(mood.emotion), 1) > 1:
            assert len(variants_seen) > 1

    def test_bitmap_is_none_by_default(self):
        engine = MoodEngine()
        session = _make_session(minutes_ago=1)
        mood = engine.compute(session)
        assert mood.bitmap is None

    def test_timestamp_is_iso_format(self):
        engine = MoodEngine()
        session = _make_session(minutes_ago=1)
        mood = engine.compute(session)
        datetime.fromisoformat(mood.timestamp)

    def test_reset_between_sessions(self):
        engine = MoodEngine()
        now = datetime.now(timezone.utc)

        happy_messages = [
            ParsedMessage(timestamp=now, text="Wonderful amazing perfect!", activity=Activity.CONVERSING)
            for _ in range(15)
        ]
        happy_session = _make_session(messages=happy_messages)
        mood1 = engine.compute(happy_session)

        sad_messages = [
            ParsedMessage(timestamp=now, text="Terrible broken awful frustrated", activity=Activity.CONVERSING)
            for _ in range(15)
        ]
        sad_session = _make_session(messages=sad_messages)
        mood2 = engine.compute(sad_session)

        assert mood1.emotion != mood2.emotion
