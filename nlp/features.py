from __future__ import annotations

import math
import re
from dataclasses import dataclass
from typing import Dict, Iterable, List, Sequence

from locale_pack.loader import LocalePack
from nlp.segmenter import Segmenter, contains_phrase, lower_tokens, ngrams


_NEGATIONS = {"not", "no", "never", "can't", "cant", "won't", "wont", "don't", "dont"}
_APOLOGY = {"sorry", "apologize", "apologies", "my bad"}
_FIRST = {"i", "i'm", "im", "me", "my", "mine"}
_SECOND = {"you", "you're", "youre", "your", "yours"}


@dataclass(frozen=True)
class FeatureContext:
    text: str
    text_l: str
    tokens: List[str]
    tokens_l: List[str]


def make_context(locale: LocalePack, text: str) -> FeatureContext:
    seg = Segmenter(locale.alphabet)
    toks = seg.tokens(text)
    toks_l = lower_tokens(toks)
    return FeatureContext(text=text, text_l=text.lower(), tokens=toks, tokens_l=toks_l)


def _count_in(tokens_l: Sequence[str], wordset: Iterable[str]) -> int:
    s = set(wordset)
    return sum(1 for t in tokens_l if t in s)


def extract_features(locale: LocalePack, text: str) -> Dict[str, float]:
    ctx = make_context(locale, text)
    lex = locale.lexicons

    feats: Dict[str, float] = {}
    feats["bias"] = 1.0

    feats["len_chars"] = float(len(ctx.text))
    feats["len_tokens"] = float(len(ctx.tokens_l))
    feats["qmarks"] = float(ctx.text.count("?"))
    feats["emarks"] = float(ctx.text.count("!"))
    feats["ellipses"] = float(ctx.text.count("..."))
    feats["newlines"] = float(ctx.text.count("\n"))

    if ctx.text:
        caps = sum(1 for c in ctx.text if c.isupper())
        letters = sum(1 for c in ctx.text if c.isalpha())
        feats["caps_ratio"] = float(caps / max(1, letters))
    else:
        feats["caps_ratio"] = 0.0

    feats["negations"] = float(sum(1 for t in ctx.tokens_l if t in _NEGATIONS))
    feats["apology"] = float(_count_in(ctx.tokens_l, _APOLOGY))
    feats["first_person"] = float(_count_in(ctx.tokens_l, _FIRST))
    feats["second_person"] = float(_count_in(ctx.tokens_l, _SECOND))

    feats["pos_hits"] = float(_count_in(ctx.tokens_l, lex.sentiment_pos))
    feats["neg_hits"] = float(_count_in(ctx.tokens_l, lex.sentiment_neg))
    feats["hedging_hits"] = float(sum(1 for phrase in lex.hedging if contains_phrase(ctx.text_l, phrase)))
    feats["minimizer_hits"] = float(sum(1 for phrase in lex.minimizers if contains_phrase(ctx.text_l, phrase)))
    feats["masking_hits"] = float(sum(1 for phrase in lex.masking_markers if contains_phrase(ctx.text_l, phrase)))
    feats["distress_hits"] = float(sum(1 for phrase in lex.distress_topics if contains_phrase(ctx.text_l, phrase)))
    feats["threat_hits"] = float(sum(1 for phrase in lex.threat if contains_phrase(ctx.text_l, phrase)))
    feats["sarcasm_hits"] = float(sum(1 for phrase in lex.sarcasm if contains_phrase(ctx.text_l, phrase)))

    # Structural patterns
    feats["contains_quote"] = float(1.0 if '"' in ctx.text or "'" in ctx.text else 0.0)
    feats["contains_but"] = float(1.0 if contains_phrase(ctx.text_l, "but") else 0.0)
    feats["contains_and"] = float(1.0 if contains_phrase(ctx.text_l, "and") else 0.0)

    # Token n-grams hashed into a small, stable space (symbolic-statistical, no embeddings).
    # This helps distinguish intents with minimal overhead.
    buckets = 64
    for ng in ngrams(ctx.tokens_l, 2):
        h = (hash(ng) & 0xFFFFFFFF) % buckets
        feats[f"bg_{h}"] = feats.get(f"bg_{h}", 0.0) + 1.0
    for t in ctx.tokens_l:
        h = (hash(t) & 0xFFFFFFFF) % buckets
        feats[f"ug_{h}"] = feats.get(f"ug_{h}", 0.0) + 1.0

    # Length transforms
    feats["log_len_tokens"] = math.log1p(feats["len_tokens"])
    feats["log_len_chars"] = math.log1p(feats["len_chars"])

    # Punctuation intensity
    feats["punct_intensity"] = float(min(3.0, feats["qmarks"] + feats["emarks"] + feats["ellipses"]))

    # Simple urgency
    feats["urgent_words"] = float(sum(1 for w in ("urgent", "asap", "now", "immediately") if contains_phrase(ctx.text_l, w)))

    # Self-harm intent hints (kept separate from generic threat words)
    feats["self_harm_phrase"] = float(
        1.0
        if any(
            contains_phrase(ctx.text_l, p)
            for p in ("kill myself", "end my life", "hurt myself", "i want to die", "i should die")
        )
        else 0.0
    )

    # Politeness / social smoothing
    feats["please"] = float(1.0 if contains_phrase(ctx.text_l, "please") else 0.0)
    feats["thanks"] = float(1.0 if contains_phrase(ctx.text_l, "thank") else 0.0)

    # Mild profanity signal (non-exhaustive)
    feats["profanity"] = float(sum(1 for w in ("fuck", "shit", "damn") if contains_phrase(ctx.text_l, w)))

    return feats

