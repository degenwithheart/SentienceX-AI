from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Iterable, List, Optional, Tuple

from nlp.segmenter import contains_phrase


@dataclass(frozen=True)
class Claim:
    key: str
    value: str
    polarity: int  # +1 / -1
    confidence: float


_SPACE_RE = re.compile(r"\s+")


def _norm(s: str) -> str:
    return _SPACE_RE.sub(" ", s.strip().lower())


def extract_claims(text: str) -> List[Claim]:
    """
    Extract simple first-person claims without heavy NLP:
    - "I am X" / "I'm X"
    - "I have X" / "I've X"
    - "I like/hate X"
    - "I don't / can't / won't X" (polarity -1)
    - "I do / can / will X" (polarity +1)

    Keys are coarse and intentionally stable for long-term memory.
    """
    tl = _norm(text)
    claims: List[Claim] = []

    def add(key: str, value: str, polarity: int, conf: float) -> None:
        k = _norm(key)
        v = _norm(value)
        if not k or not v:
            return
        claims.append(Claim(key=k, value=v, polarity=polarity, confidence=conf))

    # Identity / state
    m = re.search(r"\b(i am|i'm|im)\s+([a-z][a-z '\-]{1,48})", tl)
    if m:
        add("i_am", m.group(2), +1, 0.70)

    m = re.search(r"\b(i am not|i'm not|im not)\s+([a-z][a-z '\-]{1,48})", tl)
    if m:
        add("i_am", m.group(2), -1, 0.70)

    # Possession / conditions
    m = re.search(r"\b(i have|i've|ive)\s+([a-z][a-z '\-]{1,60})", tl)
    if m:
        add("i_have", m.group(2), +1, 0.65)
    m = re.search(r"\b(i don't have|i do not have|i havent|i haven't)\s+([a-z][a-z '\-]{1,60})", tl)
    if m:
        add("i_have", m.group(2), -1, 0.65)

    # Preferences
    m = re.search(r"\b(i like|i love)\s+([a-z][a-z '\-]{1,60})", tl)
    if m:
        add("i_like", m.group(2), +1, 0.60)
    m = re.search(r"\b(i hate)\s+([a-z][a-z '\-]{1,60})", tl)
    if m:
        add("i_like", m.group(2), -1, 0.60)

    # Capability / intention (coarse)
    if contains_phrase(tl, "i can't") or contains_phrase(tl, "i cant"):
        add("i_can", "do_it", -1, 0.55)
    if contains_phrase(tl, "i can"):
        add("i_can", "do_it", +1, 0.45)
    if contains_phrase(tl, "i won't") or contains_phrase(tl, "i wont"):
        add("i_will", "do_it", -1, 0.55)
    if contains_phrase(tl, "i will"):
        add("i_will", "do_it", +1, 0.45)

    # Deduplicate by key/value/polarity
    uniq: dict[tuple[str, str, int], Claim] = {}
    for c in claims:
        uniq[(c.key, c.value, c.polarity)] = c
    return list(uniq.values())


@dataclass(frozen=True)
class ContradictionResult:
    score: float  # 0..1
    contradictory: bool
    key: Optional[str]
    note: str


def contradiction_score(new_claims: Iterable[Claim], known_facts: Iterable[Claim]) -> ContradictionResult:
    known = list(known_facts)
    best: Tuple[float, Optional[str], str] = (0.0, None, "")

    for nc in new_claims:
        for kf in known:
            if nc.key != kf.key:
                continue
            # Direct polarity clash on same value or same key with "do_it"
            if nc.value == kf.value and nc.polarity != kf.polarity:
                s = min(1.0, 0.55 + 0.45 * min(nc.confidence, kf.confidence))
                if s > best[0]:
                    best = (s, nc.key, "polarity_flip_same_value")
            elif nc.key in {"i_am", "i_have", "i_like"} and nc.polarity == +1 and kf.polarity == +1 and nc.value != kf.value:
                # Non-exclusive contradictions: keep gentle (people change).
                s = 0.25 * min(nc.confidence, kf.confidence)
                if s > best[0]:
                    best = (s, nc.key, "different_value_same_key")

    score, key, note = best
    return ContradictionResult(score=score, contradictory=score >= 0.60, key=key, note=note)

