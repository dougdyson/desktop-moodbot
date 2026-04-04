from parsers.base import ParsedMessage
from .sentiment import score_text, emotional_weight

FAILURE_PER_ERROR = -0.03
FAILURE_CONSECUTIVE_BONUS = -0.05
FAILURE_CONSECUTIVE_THRESHOLD = 3
FAILURE_CLAMP_MIN = -0.25

CONTEXT_USER_SCALE = 0.3
CONTEXT_CLAMP_MIN = -0.15
CONTEXT_CLAMP_MAX = 0.15


def compute_failure_modifier(messages: list[ParsedMessage]) -> float:
    modifier = 0.0
    consecutive_errors = 0

    for msg in messages:
        if msg.is_error:
            modifier += FAILURE_PER_ERROR
            consecutive_errors += 1
            if consecutive_errors >= FAILURE_CONSECUTIVE_THRESHOLD:
                modifier += FAILURE_CONSECUTIVE_BONUS
                consecutive_errors = 0
        else:
            consecutive_errors = 0

    return max(FAILURE_CLAMP_MIN, min(0.0, modifier))


def compute_context_modifier(messages: list[ParsedMessage]) -> float:
    user_scores: list[tuple[float, float]] = []

    for msg in messages:
        if msg.role != "user":
            continue
        if not msg.text.strip():
            continue
        raw = score_text(msg.text)
        weight = emotional_weight(msg.text)
        user_scores.append((raw, weight))

    if not user_scores:
        return 0.0

    total_weight = sum(w for _, w in user_scores)
    if total_weight == 0:
        return 0.0

    avg = sum(s * w for s, w in user_scores) / total_weight
    modifier = avg * CONTEXT_USER_SCALE

    return max(CONTEXT_CLAMP_MIN, min(CONTEXT_CLAMP_MAX, modifier))
