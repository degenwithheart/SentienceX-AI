from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Optional

from memory.semantic import SemanticMemory
from cognition.learned import proactive_priors


@dataclass(frozen=True)
class ProactivePrompt:
    topic: str
    kind: str  # "unresolved" | "trend"


def choose_proactive(
    semantic: SemanticMemory,
    min_hours_gap: int,
    has_recent: bool,
    style_avg_tokens: Optional[float] = None,
) -> Optional[ProactivePrompt]:
    now = time.time()
    if has_recent:
        return None

    # Prefer unresolved topics; then strongest topic by salience.
    if semantic.unresolved:
        topic, ts = sorted(semantic.unresolved.items(), key=lambda kv: kv[1])[0]
        hours = (now - ts) / 3600.0
        if hours >= min_hours_gap:
            return ProactivePrompt(topic=topic, kind="unresolved")

    if semantic.topics:
        topic, sal = sorted(semantic.topics.items(), key=lambda kv: kv[1], reverse=True)[0]
        if sal >= 0.35 and (now - semantic.last_turn_ts) / 3600.0 >= min_hours_gap:
            return ProactivePrompt(topic=topic, kind="trend")

    # Learned behavior pattern: if distress is high and the user tends to shorten up, check in gently.
    pri = proactive_priors()
    if pri is not None:
        try:
            rules = pri.get("rules", {}) or {}
            wd = rules.get("withdrawal_after_distress", {}) or {}
            p = float(wd.get("p", 0.0))
            if p >= 0.40:
                dist = float(semantic.emotions.get("distress", 0.0))
                if dist >= float(wd.get("min_distress", 0.70)) - 0.10:
                    if style_avg_tokens is None or style_avg_tokens <= 8.5:
                        topic = "that"
                        if semantic.topics:
                            topic = sorted(semantic.topics.items(), key=lambda kv: kv[1], reverse=True)[0][0]
                        if (now - semantic.last_turn_ts) / 3600.0 >= min_hours_gap:
                            return ProactivePrompt(topic=topic, kind="trend")
        except Exception:
            pass

    return None
