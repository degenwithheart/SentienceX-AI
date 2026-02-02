from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List

from cognition.hidden_emotion import infer_hidden_distress
from locale_pack.loader import LocalePack
from nlp.features import make_context
from style.extractor import extract_style


def _root() -> Path:
    return Path(__file__).resolve().parents[2]


def mine_proactive_patterns(locale: LocalePack, data_dir: Path, conversations: Dict[str, object]) -> Dict[str, object]:
    convs = conversations.get("convs", [])
    if not convs:
        out = {"version": 1, "source": "TRAIN/raw_conversations", "rules": {}, "stats": {}}
        (_root() / "cognition" / "proactive_priors.json").write_text(json.dumps(out, ensure_ascii=False), encoding="utf-8")
        return {"exported": ["cognition/proactive_priors.json"], "conversations": 0}

    withdraw_after_distress = 0
    after_total = 0
    topic_repeat = 0
    topic_total = 0

    for c in convs:
        turns = c.turns  # type: ignore[attr-defined]
        # Track user shortness after distressful user message.
        last_user_distress = 0.0
        last_user_tokens = 0
        for t in turns:
            if t.role != "user":
                continue
            ctx = make_context(locale, t.text)
            hidden = infer_hidden_distress(locale, t.text)
            if last_user_distress >= 0.70:
                after_total += 1
                if len(ctx.tokens_l) <= max(5, int(last_user_tokens * 0.6)):
                    withdraw_after_distress += 1
            last_user_distress = hidden.distress_score
            last_user_tokens = len(ctx.tokens_l)

        # Topic repetition: crude measure using distress topics lexicon.
        seen = set()
        for t in turns:
            if t.role != "user":
                continue
            tl = t.text.lower()
            for phrase in locale.lexicons.distress_topics:
                if phrase in tl:
                    topic_total += 1
                    if phrase in seen:
                        topic_repeat += 1
                    seen.add(phrase)

    p_withdraw = (withdraw_after_distress / after_total) if after_total else 0.0
    p_repeat = (topic_repeat / topic_total) if topic_total else 0.0

    rules = {
        "withdrawal_after_distress": {"p": p_withdraw, "min_distress": 0.70, "max_tokens_ratio": 0.60},
        "topic_repetition": {"p": p_repeat, "note": "repeated distress topic mentions"},
    }
    out = {
        "version": 1,
        "source": "TRAIN/raw_conversations",
        "rules": rules,
        "stats": {"after_total": after_total, "topic_total": topic_total},
    }
    cog_dir = _root() / "cognition"
    cog_dir.mkdir(parents=True, exist_ok=True)
    (cog_dir / "proactive_priors.json").write_text(json.dumps(out, ensure_ascii=False), encoding="utf-8")
    return {"exported": ["cognition/proactive_priors.json"], "stats": out["stats"], "rules": rules}
