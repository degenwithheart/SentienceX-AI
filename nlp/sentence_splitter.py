from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Iterable, List, Set


_SENT_END_RE = re.compile(r"([.!?]+)(\s+|\n+)")


@dataclass(frozen=True)
class Sentence:
    text: str


class SentenceSplitter:
    def __init__(self, abbreviations: Set[str]):
        self._abbr = {a.strip() for a in abbreviations if a.strip()}

    def split(self, text: str) -> List[Sentence]:
        s = text.strip()
        if not s:
            return []

        parts: List[str] = []
        start = 0
        for m in _SENT_END_RE.finditer(s):
            end = m.end(1)
            candidate = s[start:end].strip()
            if candidate:
                last_token = candidate.split()[-1]
                if last_token in self._abbr:
                    continue
                parts.append(candidate)
                start = m.end()

        tail = s[start:].strip()
        if tail:
            parts.append(tail)
        return [Sentence(text=p) for p in parts]


def join_sentences(sentences: Iterable[Sentence]) -> str:
    return " ".join(s.text for s in sentences).strip()

