import pytest

from core.sentiment import (
    EmotionBand,
    SentimentScorer,
    emotional_weight,
    score_text,
    score_to_band,
)


class TestScoreText:
    def test_positive_text(self):
        score = score_text("This is absolutely wonderful and I love it!")
        assert score > 0.3

    def test_negative_text(self):
        score = score_text("This is terrible and completely broken, very frustrating")
        assert score < -0.3

    def test_neutral_text(self):
        score = score_text("The function returns a list of integers")
        assert -0.3 < score < 0.3

    def test_empty_text(self):
        assert score_text("") == 0.0
        assert score_text("   ") == 0.0


class TestEmotionalWeight:
    def test_emotional_text_gets_high_weight(self):
        weight = emotional_weight("I'm so excited! This is amazing and wonderful!")
        assert weight > 0.6

    def test_technical_text_gets_low_weight(self):
        weight = emotional_weight("```python\ndef function():\n    return class.import\n```")
        assert weight < 0.5

    def test_mixed_text_gets_middle_weight(self):
        weight = emotional_weight("I think this function is great but the return value seems wrong")
        assert 0.3 < weight < 0.9

    def test_empty_text_gets_minimum(self):
        assert emotional_weight("") == 0.2

    def test_weight_always_between_bounds(self):
        texts = [
            "!!!!!!!!!!! AMAZING WONDERFUL FANTASTIC!!!!!",
            "def foo(): return bar()",
            "",
            "a",
            "I feel worried and confused about this terrible awful broken mess",
        ]
        for text in texts:
            w = emotional_weight(text)
            assert 0.2 <= w <= 1.0, f"Weight {w} out of bounds for: {text}"


class TestScoreToBand:
    def test_negative_score(self):
        assert score_to_band(-0.5) == EmotionBand.NEGATIVE

    def test_uneasy_score(self):
        assert score_to_band(-0.2) == EmotionBand.UNEASY

    def test_neutral_score(self):
        assert score_to_band(0.0) == EmotionBand.NEUTRAL

    def test_positive_score(self):
        assert score_to_band(0.3) == EmotionBand.POSITIVE

    def test_elated_score(self):
        assert score_to_band(0.6) == EmotionBand.ELATED

    def test_boundary_negative_uneasy(self):
        assert score_to_band(-0.35) == EmotionBand.UNEASY
        assert score_to_band(-0.36) == EmotionBand.NEGATIVE

    def test_boundary_neutral_positive(self):
        assert score_to_band(0.15) == EmotionBand.POSITIVE
        assert score_to_band(0.14) == EmotionBand.NEUTRAL


class TestSentimentScorer:
    def test_starts_neutral(self):
        scorer = SentimentScorer()
        assert scorer.current_band == EmotionBand.NEUTRAL
        assert scorer.current_score == 0.0

    def test_positive_messages_shift_band(self):
        scorer = SentimentScorer()
        for _ in range(15):
            scorer.add_message("This is absolutely wonderful! I love it so much!")
        assert scorer.current_band in (EmotionBand.POSITIVE, EmotionBand.ELATED)

    def test_negative_messages_shift_band(self):
        scorer = SentimentScorer()
        for _ in range(15):
            scorer.add_message("This is terrible, broken, and frustrating to deal with")
        assert scorer.current_band in (EmotionBand.NEGATIVE, EmotionBand.UNEASY)

    def test_hysteresis_prevents_flickering(self):
        scorer = SentimentScorer()
        for _ in range(15):
            scorer.add_message("Everything is great and wonderful today!")
        band_before = scorer.current_band

        scorer.add_message("The function returns a list")
        assert scorer.current_band == band_before

    def test_window_size_limits_history(self):
        scorer = SentimentScorer(window_size=5)
        for _ in range(10):
            scorer.add_message("This is absolutely terrible and awful!")

        for _ in range(5):
            scorer.add_message("This is absolutely wonderful and amazing and perfect!")

        assert scorer.current_score > 0

    def test_empty_message_preserves_band(self):
        scorer = SentimentScorer()
        for _ in range(15):
            scorer.add_message("This is great and wonderful!")
        band = scorer.current_band

        scorer.add_message("")
        assert scorer.current_band == band

    def test_reset_clears_state(self):
        scorer = SentimentScorer()
        for _ in range(15):
            scorer.add_message("This is wonderful!")

        scorer.reset()
        assert scorer.current_band == EmotionBand.NEUTRAL
        assert scorer.current_score == 0.0

    def test_adjacent_band_transitions(self):
        scorer = SentimentScorer(hysteresis=0.0)
        bands_seen = set()
        messages = [
            ("Everything is wonderful and amazing!", 15),
            ("The function returns a value", 15),
            ("This is terrible and broken", 15),
        ]
        for msg, count in messages:
            for _ in range(count):
                band = scorer.add_message(msg)
                bands_seen.add(band)
        assert len(bands_seen) >= 2
