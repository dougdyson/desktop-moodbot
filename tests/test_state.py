import json
from datetime import datetime, timezone, timedelta
from pathlib import Path

import pytest

from core.sentiment import EmotionBand
from core.state import MoodEngine, MoodState, VARIANT_COUNTS, EMOJI_MATRIX, SLEEPING_EMOJI
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

    def test_to_dict_includes_emoji(self):
        state = MoodState(
            activity="thinking",
            emotion="neutral",
            variant=0,
            timestamp="2026-02-20T14:30:00Z",
            sleeping=False,
            emoji="\U0001f914",
        )
        d = state.to_dict()
        assert d["emoji"] == "\U0001f914"

    def test_to_dict_is_json_serializable(self):
        state = MoodState(
            activity="reading",
            emotion="neutral",
            variant=0,
            timestamp="2026-02-20T14:30:00Z",
            sleeping=True,
            emoji="\U0001f440",
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

    def test_bitmap_present_when_sprites_exist(self):
        engine = MoodEngine()
        session = _make_session(minutes_ago=1)
        mood = engine.compute(session)
        assert isinstance(mood.bitmap, str)
        assert len(mood.bitmap) > 0

    def test_timestamp_is_iso_format(self):
        engine = MoodEngine()
        session = _make_session(minutes_ago=1)
        mood = engine.compute(session)
        datetime.fromisoformat(mood.timestamp)

    def test_emoji_present_in_output(self):
        engine = MoodEngine()
        session = _make_session(minutes_ago=1)
        mood = engine.compute(session)
        assert mood.emoji != ""
        assert isinstance(mood.emoji, str)

    def test_emoji_matches_activity_emotion(self):
        engine = MoodEngine()
        session = _make_session(minutes_ago=1)
        mood = engine.compute(session)
        expected = EMOJI_MATRIX.get((mood.activity, mood.emotion))
        assert mood.emoji == expected

    def test_sleeping_emoji_override(self):
        engine = MoodEngine(sleep_timeout=1)
        session = _make_session(minutes_ago=60)
        mood = engine.compute(session)
        assert mood.sleeping is True
        assert mood.emoji == SLEEPING_EMOJI

    def test_emoji_covers_all_matrix_entries(self):
        activities = ["thinking", "conversing", "reading", "executing", "editing", "system"]
        emotions = ["negative", "uneasy", "neutral", "positive", "elated"]
        for act in activities:
            for emo in emotions:
                assert (act, emo) in EMOJI_MATRIX, f"Missing emoji for ({act}, {emo})"

    def test_compute_with_failure_signals(self):
        engine = MoodEngine()
        now = datetime.now(timezone.utc)
        messages = [
            ParsedMessage(
                timestamp=now,
                text="Neutral technical response here",
                activity=Activity.CONVERSING,
            )
            for _ in range(10)
        ]
        for _ in range(5):
            messages.append(ParsedMessage(
                timestamp=now,
                text="Error: command failed",
                activity=Activity.EXECUTING,
                role="tool_result",
                is_error=True,
            ))
        session_with_errors = _make_session(messages=messages)

        clean_messages = [
            ParsedMessage(
                timestamp=now,
                text="Neutral technical response here",
                activity=Activity.CONVERSING,
            )
            for _ in range(15)
        ]
        session_clean = _make_session(messages=clean_messages)

        mood_errors = engine.compute(session_with_errors)
        mood_clean = engine.compute(session_clean)
        assert mood_errors.sentiment_score < mood_clean.sentiment_score

    def test_compute_with_positive_context(self):
        engine = MoodEngine()
        now = datetime.now(timezone.utc)
        messages = [
            ParsedMessage(
                timestamp=now,
                text="Neutral technical response here",
                activity=Activity.CONVERSING,
            )
            for _ in range(10)
        ]
        for _ in range(5):
            messages.append(ParsedMessage(
                timestamp=now,
                text="Thanks so much, that's perfect and amazing!",
                activity=Activity.CONVERSING,
                role="user",
            ))
        session = _make_session(messages=messages)

        clean_messages = [
            ParsedMessage(
                timestamp=now,
                text="Neutral technical response here",
                activity=Activity.CONVERSING,
            )
            for _ in range(15)
        ]
        session_clean = _make_session(messages=clean_messages)

        mood_with_context = engine.compute(session)
        mood_clean = engine.compute(session_clean)
        assert mood_with_context.sentiment_score > mood_clean.sentiment_score

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
