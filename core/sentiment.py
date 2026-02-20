import math
import re
from enum import Enum

from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

EMOTIONAL_PUNCTUATION = re.compile(r"[!?]")
EPISTEMIC_PHRASES = re.compile(
    r"\b(i think|i believe|i feel|i wonder|i hope|i wish)\b", re.IGNORECASE
)
POSITIVE_ADJECTIVES = re.compile(
    r"\b(great|excellent|awesome|happy|wonderful|fantastic|perfect|amazing|love|excited)\b",
    re.IGNORECASE,
)
NEGATIVE_ADJECTIVES = re.compile(
    r"\b(sorry|frustrated|worried|annoying|broken|failed|wrong|terrible|awful|confused)\b",
    re.IGNORECASE,
)
UNCERTAINTY_WORDS = re.compile(
    r"\b(maybe|perhaps|might|seems|possibly|unclear|unsure)\b", re.IGNORECASE
)
CODE_BLOCKS = re.compile(r"```")
INLINE_CODE = re.compile(r"`[^`]+`")
TECHNICAL_KEYWORDS = re.compile(
    r"\b(function|class|import|def|return|const|let|var|async|await)\b"
)
TECHNICAL_PUNCTUATION = re.compile(r"[{}\[\]();]")


class EmotionBand(Enum):
    NEGATIVE = "negative"
    UNEASY = "uneasy"
    NEUTRAL = "neutral"
    POSITIVE = "positive"
    ELATED = "elated"


BAND_THRESHOLDS = [
    (-0.35, EmotionBand.NEGATIVE),
    (-0.10, EmotionBand.UNEASY),
    (0.15, EmotionBand.NEUTRAL),
    (0.45, EmotionBand.POSITIVE),
    (float("inf"), EmotionBand.ELATED),
]

BAND_CENTERS = {
    EmotionBand.NEGATIVE: -0.55,
    EmotionBand.UNEASY: -0.225,
    EmotionBand.NEUTRAL: 0.025,
    EmotionBand.POSITIVE: 0.30,
    EmotionBand.ELATED: 0.60,
}

HYSTERESIS = 0.08
WINDOW_SIZE = 15

_analyzer = SentimentIntensityAnalyzer()


def score_text(text: str) -> float:
    if not text.strip():
        return 0.0
    return _analyzer.polarity_scores(text)["compound"]


def emotional_weight(text: str) -> float:
    words = text.split()
    word_count = len(words)
    if word_count == 0:
        return 0.2

    emotional_signals = (
        len(EMOTIONAL_PUNCTUATION.findall(text)) * 0.5
        + len(EPISTEMIC_PHRASES.findall(text)) * 2
        + len(POSITIVE_ADJECTIVES.findall(text)) * 3
        + len(NEGATIVE_ADJECTIVES.findall(text)) * 3
        + len(UNCERTAINTY_WORDS.findall(text)) * 1
    )

    technical_signals = (
        len(CODE_BLOCKS.findall(text)) * 2
        + len(INLINE_CODE.findall(text)) * 0.5
        + len(TECHNICAL_KEYWORDS.findall(text)) * 0.5
        + len(TECHNICAL_PUNCTUATION.findall(text)) * 0.1
    )

    emotional_density = emotional_signals / math.sqrt(word_count)
    technical_density = technical_signals / math.sqrt(word_count)

    weight = 0.2 + 0.8 * (emotional_density / (emotional_density + technical_density + 0.1))
    return max(0.2, min(1.0, weight))


def score_to_band(score: float) -> EmotionBand:
    for threshold, band in BAND_THRESHOLDS:
        if score < threshold:
            return band
    return EmotionBand.ELATED


class SentimentScorer:
    def __init__(self, window_size: int = WINDOW_SIZE, hysteresis: float = HYSTERESIS):
        self.window_size = window_size
        self.hysteresis = hysteresis
        self._scores: list[tuple[float, float]] = []
        self._current_band: EmotionBand = EmotionBand.NEUTRAL

    @property
    def current_band(self) -> EmotionBand:
        return self._current_band

    @property
    def current_score(self) -> float:
        if not self._scores:
            return 0.0
        return self._weighted_average()

    def add_message(self, text: str) -> EmotionBand:
        if not text.strip():
            return self._current_band

        raw_score = score_text(text)
        weight = emotional_weight(text)
        self._scores.append((raw_score, weight))

        if len(self._scores) > self.window_size:
            self._scores = self._scores[-self.window_size:]

        avg = self._weighted_average()
        candidate_band = score_to_band(avg)

        if candidate_band != self._current_band:
            current_center = BAND_CENTERS[self._current_band]
            if abs(avg - current_center) > self.hysteresis:
                self._current_band = candidate_band

        return self._current_band

    def _weighted_average(self) -> float:
        if not self._scores:
            return 0.0
        total_weight = sum(w for _, w in self._scores)
        if total_weight == 0:
            return 0.0
        return sum(s * w for s, w in self._scores) / total_weight

    def reset(self) -> None:
        self._scores.clear()
        self._current_band = EmotionBand.NEUTRAL
