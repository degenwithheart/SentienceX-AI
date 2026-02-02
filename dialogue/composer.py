from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

from locale_pack.loader import LocalePack
from learning.online_update import OnlineUpdater
from memory.persistence import RetrievedMemory


@dataclass(frozen=True)
class Composed:
    text: str
    template_id: str
    tone: str


def _safe_format(tpl: str, slots: Dict[str, str]) -> str:
    out = tpl
    for k, v in slots.items():
        out = out.replace("{" + k + "}", v)
    return out


def reflect_phrase(sentiment_label: str, hidden_score: float, masking: bool) -> str:
    if hidden_score >= 0.70 and masking:
        return "I’m noticing a lot under the surface. "
    if sentiment_label == "neg":
        return "That sounds rough. "
    if sentiment_label == "pos" and hidden_score < 0.35:
        return "I hear you. "
    return "I’m with you. "


def pick_template(locale: LocalePack, updater: OnlineUpdater, tone: str, brevity: str, seed: int) -> dict:
    groups = {
        "normal": locale.templates.normal,
        "empathy": locale.templates.empathy,
        "ack_short": locale.templates.ack_short,
        "proactive": locale.templates.proactive,
        "safety": locale.templates.safety,
    }
    candidates = [t for t in groups.get(tone, locale.templates.normal) if brevity in t.get("brevity", ["normal"])]
    if not candidates:
        candidates = groups.get(tone, locale.templates.normal) or locale.templates.normal

    ids = [c["id"] for c in candidates]
    chosen_id = updater.template_ranker.pick(ids, seed=seed)
    for c in candidates:
        if c["id"] == chosen_id:
            return c
    return candidates[0]


def compose(locale: LocalePack, updater: OnlineUpdater, tone: str, brevity: str, slots: Dict[str, str]) -> Composed:
    seed = int(time.time()) ^ hash((tone, brevity, slots.get("topic", "")))
    tpl = pick_template(locale, updater, tone=tone, brevity=brevity, seed=seed)
    text = _safe_format(tpl["text"], slots=slots)
    return Composed(text=text, template_id=tpl["id"], tone=tpl.get("tone", tone))

