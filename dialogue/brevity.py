from __future__ import annotations

from dataclasses import dataclass

from locale_pack.loader import LocalePack
from style.profile import StyleProfile


def choose_brevity(locale: LocalePack, style: StyleProfile, hidden_distress: float, user_tokens: int) -> str:
    # Micro when user is very short, or when we suspect they're overwhelmed and just need presence.
    if hidden_distress >= 0.75 and user_tokens <= 14:
        return "short"
    if user_tokens <= 5:
        return "micro"
    if style.avg_tokens <= 8:
        return "short"
    return "normal"

