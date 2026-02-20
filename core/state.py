import random
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional

from parsers.base import Activity, ParsedMessage, ParsedSession
from .sentiment import EmotionBand, SentimentScorer

VARIANT_COUNTS = {
    EmotionBand.NEGATIVE: 1,
    EmotionBand.UNEASY: 2,
    EmotionBand.NEUTRAL: 4,
    EmotionBand.POSITIVE: 4,
    EmotionBand.ELATED: 1,
}

SLEEP_TIMEOUT_SECONDS = 30 * 60


@dataclass
class MoodState:
    activity: str
    emotion: str
    variant: int
    timestamp: str
    sleeping: bool
    bitmap: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "activity": self.activity,
            "emotion": self.emotion,
            "variant": self.variant,
            "timestamp": self.timestamp,
            "sleeping": self.sleeping,
            "bitmap": self.bitmap,
        }


class MoodEngine:
    def __init__(self, sleep_timeout: int = SLEEP_TIMEOUT_SECONDS):
        self.scorer = SentimentScorer()
        self.sleep_timeout = sleep_timeout
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

        now = datetime.now(timezone.utc).isoformat()

        return MoodState(
            activity=activity.value,
            emotion=emotion.value,
            variant=variant,
            timestamp=now,
            sleeping=sleeping,
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
