from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class FeedbackSignal:
    kind: str  # "explicit" | "implicit"
    success: bool
    weight: float
    template_id: Optional[str]
    tone: Optional[str]


def parse_explicit(payload: dict) -> FeedbackSignal:
    # Expected: {"rating": 1|-1, "template_id": "...", "tone": "..."}
    rating = int(payload.get("rating", 0))
    success = rating > 0
    weight = 1.0 if rating != 0 else 0.2
    return FeedbackSignal(
        kind="explicit",
        success=success,
        weight=weight,
        template_id=payload.get("template_id"),
        tone=payload.get("tone"),
    )


def implicit_from_engagement(seconds_to_reply: float) -> FeedbackSignal:
    # Faster replies indicate the response "landed" (imperfect but useful).
    if seconds_to_reply <= 60:
        return FeedbackSignal(kind="implicit", success=True, weight=0.35, template_id=None, tone=None)
    if seconds_to_reply <= 7 * 60:
        return FeedbackSignal(kind="implicit", success=True, weight=0.20, template_id=None, tone=None)
    if seconds_to_reply <= 20 * 60:
        return FeedbackSignal(kind="implicit", success=False, weight=0.15, template_id=None, tone=None)
    return FeedbackSignal(kind="implicit", success=False, weight=0.25, template_id=None, tone=None)

