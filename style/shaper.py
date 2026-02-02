from __future__ import annotations

import re
from dataclasses import dataclass

from locale_pack.loader import LocalePack
from style.profile import StyleProfile


_MULTISPACE_RE = re.compile(r"[ \t]{2,}")


def _sentence_count(text: str) -> int:
    if not text.strip():
        return 0
    return sum(1 for ch in text if ch in ".!?") or 1


@dataclass(frozen=True)
class Shaped:
    text: str
    brevity: str


def shape_reply(locale: LocalePack, style: StyleProfile, text: str, target_brevity: str, max_chars: int) -> Shaped:
    s = _MULTISPACE_RE.sub(" ", text.strip())
    s = s[:max_chars].rstrip()

    rules = locale.style_rules
    max_emojis = int(rules.get("max_emojis_per_reply", 0))
    if max_emojis == 0:
        # Remove common emoji ranges without relying on large tables.
        s = re.sub(r"[\U0001F300-\U0001FAFF\U00002600-\U000027BF]+", "", s)

    # Enforce brevity via sentence clipping.
    max_sentences = {
        "micro": int(rules.get("max_sentences_micro", 1)),
        "short": int(rules.get("max_sentences_short", 2)),
        "normal": int(rules.get("max_sentences_normal", 5)),
    }.get(target_brevity, 3)

    if _sentence_count(s) > max_sentences:
        # Clip to max sentences by scanning punctuation.
        out = []
        count = 0
        for ch in s:
            out.append(ch)
            if ch in ".!?":
                count += 1
                if count >= max_sentences:
                    break
        s = "".join(out).strip()

    # Match user's directness slightly (avoid over-mirroring).
    if style.directness < 0.35 and not s.lower().startswith(("maybe", "i think", "it might")):
        if target_brevity != "micro":
            s = "Maybe " + s[0].lower() + s[1:] if s else s

    return Shaped(text=s, brevity=target_brevity)

