from __future__ import annotations

import re
from dataclasses import dataclass
from typing import List

from locale_pack.loader import LocalePack
from nlp.features import extract_features, make_context


_EMOJI_RE = re.compile(
    "[\U0001F300-\U0001FAFF\U00002600-\U000027BF]",
    flags=re.UNICODE,
)


@dataclass(frozen=True)
class StyleSignals:
    tokens: int
    emojis: int
    exclaims: int
    questions: int
    hedges: int


def extract_style(locale: LocalePack, text: str) -> StyleSignals:
    ctx = make_context(locale, text)
    feats = extract_features(locale, text)
    emojis = len(_EMOJI_RE.findall(text))
    return StyleSignals(
        tokens=len(ctx.tokens_l),
        emojis=emojis,
        exclaims=int(feats.get("emarks", 0.0)),
        questions=int(feats.get("qmarks", 0.0)),
        hedges=int(feats.get("hedging_hits", 0.0)),
    )

