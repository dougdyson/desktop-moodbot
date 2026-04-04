from datetime import datetime, timezone

import pytest

from core.signals import (
    CONTEXT_CLAMP_MAX,
    CONTEXT_CLAMP_MIN,
    FAILURE_CLAMP_MIN,
    FAILURE_CONSECUTIVE_BONUS,
    FAILURE_PER_ERROR,
    compute_context_modifier,
    compute_failure_modifier,
)
from parsers.base import Activity, ParsedMessage


def _msg(
    text="Some technical response",
    role="assistant",
    is_error=False,
    activity=Activity.CONVERSING,
):
    return ParsedMessage(
        timestamp=datetime.now(timezone.utc),
        text=text,
        activity=activity,
        role=role,
        is_error=is_error,
    )


class TestFailureModifier:
    def test_no_errors(self):
        messages = [_msg() for _ in range(5)]
        assert compute_failure_modifier(messages) == 0.0

    def test_single_error(self):
        messages = [_msg(), _msg(is_error=True), _msg()]
        result = compute_failure_modifier(messages)
        assert result == pytest.approx(FAILURE_PER_ERROR)

    def test_consecutive_errors(self):
        messages = [_msg(is_error=True) for _ in range(3)]
        result = compute_failure_modifier(messages)
        expected = (3 * FAILURE_PER_ERROR) + FAILURE_CONSECUTIVE_BONUS
        assert result == pytest.approx(expected)

    def test_clamped(self):
        messages = [_msg(is_error=True) for _ in range(50)]
        result = compute_failure_modifier(messages)
        assert result == pytest.approx(FAILURE_CLAMP_MIN)


class TestContextModifier:
    def test_positive_user_message(self):
        messages = [
            _msg(),
            _msg(text="Thanks, that's exactly right! Great work!", role="user"),
        ]
        result = compute_context_modifier(messages)
        assert result > 0.0

    def test_negative_user_message(self):
        messages = [
            _msg(),
            _msg(text="This is totally broken and wrong, very frustrated", role="user"),
        ]
        result = compute_context_modifier(messages)
        assert result < 0.0

    def test_no_user_messages(self):
        messages = [_msg() for _ in range(5)]
        assert compute_context_modifier(messages) == 0.0

    def test_ignores_assistant_messages(self):
        messages = [
            _msg(text="This is wonderful and amazing!", role="assistant"),
        ]
        assert compute_context_modifier(messages) == 0.0

    def test_clamped(self):
        messages = [
            _msg(
                text="AMAZING WONDERFUL FANTASTIC PERFECT EXCELLENT LOVE IT!!!",
                role="user",
            )
            for _ in range(15)
        ]
        result = compute_context_modifier(messages)
        assert result <= CONTEXT_CLAMP_MAX

        messages = [
            _msg(
                text="TERRIBLE AWFUL BROKEN HORRIBLE DISGUSTING HATE IT!!!",
                role="user",
            )
            for _ in range(15)
        ]
        result = compute_context_modifier(messages)
        assert result >= CONTEXT_CLAMP_MIN

    def test_scales_by_weight(self):
        emotional = [
            _msg(text="I'm so happy and excited about this! Wonderful!", role="user"),
        ]
        technical = [
            _msg(text="ok the `function getData()` returns `const x = 1`", role="user"),
        ]
        emotional_result = compute_context_modifier(emotional)
        technical_result = compute_context_modifier(technical)
        assert abs(emotional_result) > abs(technical_result)
