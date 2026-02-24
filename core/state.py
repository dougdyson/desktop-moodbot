import random
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional

from parsers.base import Activity, ParsedMessage, ParsedSession
from sprites.manifest import SpriteManifest
from .sentiment import EmotionBand, SentimentScorer

VARIANT_COUNTS = {
    EmotionBand.NEGATIVE: 1,
    EmotionBand.UNEASY: 2,
    EmotionBand.NEUTRAL: 4,
    EmotionBand.POSITIVE: 4,
    EmotionBand.ELATED: 1,
}

EMOJI_MATRIX: dict[tuple[str, str], str] = {
    ("thinking", "negative"): "\U0001f623",
    ("thinking", "uneasy"): "\U0001f615",
    ("thinking", "neutral"): "\U0001f914",
    ("thinking", "positive"): "\U0001f4ad",
    ("thinking", "elated"): "\U0001f9e0",
    ("conversing", "negative"): "\U0001f624",
    ("conversing", "uneasy"): "\U0001f61f",
    ("conversing", "neutral"): "\U0001f5e3\ufe0f",
    ("conversing", "positive"): "\U0001f60a",
    ("conversing", "elated"): "\U0001f929",
    ("reading", "negative"): "\U0001f616",
    ("reading", "uneasy"): "\U0001f9d0",
    ("reading", "neutral"): "\U0001f440",
    ("reading", "positive"): "\U0001f4d6",
    ("reading", "elated"): "\U0001f50e",
    ("executing", "negative"): "\U0001f4a5",
    ("executing", "uneasy"): "\u26a0\ufe0f",
    ("executing", "neutral"): "\u2699\ufe0f",
    ("executing", "positive"): "\u26a1",
    ("executing", "elated"): "\U0001f680",
    ("editing", "negative"): "\U0001f629",
    ("editing", "uneasy"): "\U0001f62c",
    ("editing", "neutral"): "\u270f\ufe0f",
    ("editing", "positive"): "\u270d\ufe0f",
    ("editing", "elated"): "\U0001f4dd",
    ("system", "negative"): "\U0001f534",
    ("system", "uneasy"): "\U0001f7e1",
    ("system", "neutral"): "\U0001f527",
    ("system", "positive"): "\U0001f504",
    ("system", "elated"): "\u2705",
}

SLEEPING_EMOJI = "\U0001f634"

SLEEP_TIMEOUT_SECONDS = 30 * 60


@dataclass
class MoodState:
    activity: str
    emotion: str
    variant: int
    timestamp: str
    sleeping: bool
    emoji: str = ""
    bitmap: Optional[str] = None
    sentiment_score: float = 0.0

    def to_dict(self) -> dict:
        return {
            "activity": self.activity,
            "emotion": self.emotion,
            "variant": self.variant,
            "timestamp": self.timestamp,
            "sleeping": self.sleeping,
            "emoji": self.emoji,
            "bitmap": self.bitmap,
            "sentiment_score": round(self.sentiment_score, 3),
        }


class MoodEngine:
    def __init__(self, sleep_timeout: int = SLEEP_TIMEOUT_SECONDS,
                 sprites: Optional[SpriteManifest] = None):
        self.scorer = SentimentScorer()
        self.sleep_timeout = sleep_timeout
        self.sprites = sprites or SpriteManifest()
        self._last_activity = Activity.THINKING
        self._last_variant: dict[tuple[str, str], int] = {}

    def compute(self, session: ParsedSession) -> MoodState:
        self.scorer.reset()

        for msg in session.messages:
            if msg.text:
                self.scorer.add_message(msg.text)
            self._last_activity = msg.activity

        emotion = self.scorer.current_band
        activity = self._last_activity
        sleeping = self._is_sleeping(session)

        variant = self._pick_variant(activity, emotion)

        bitmap = self.sprites.lookup(
            activity.value, emotion.value, variant, sleeping=sleeping
        )

        if sleeping:
            emoji = SLEEPING_EMOJI
        else:
            emoji = EMOJI_MATRIX.get((activity.value, emotion.value), "")

        now = datetime.now(timezone.utc).isoformat()

        return MoodState(
            activity=activity.value,
            emotion=emotion.value,
            variant=variant,
            timestamp=now,
            sleeping=sleeping,
            emoji=emoji,
            bitmap=bitmap,
            sentiment_score=self.scorer.current_score,
        )

    def _is_sleeping(self, session: ParsedSession) -> bool:
        last_time = session.last_activity_time
        if not last_time:
            return True
        now = datetime.now(timezone.utc)
        if last_time.tzinfo is None:
            from datetime import timezone as tz
            last_time = last_time.replace(tzinfo=tz.utc)
        elapsed = (now - last_time).total_seconds()
        return elapsed > self.sleep_timeout

    def _pick_variant(self, activity: Activity, emotion: EmotionBand) -> int:
        max_variants = VARIANT_COUNTS.get(emotion, 1)
        if max_variants <= 1:
            return 0

        key = (activity.value, emotion.value)
        last = self._last_variant.get(key)
        choices = [i for i in range(max_variants) if i != last]
        variant = random.choice(choices) if choices else 0
        self._last_variant[key] = variant
        return variant
