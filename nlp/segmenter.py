from __future__ import annotations

from dataclasses import dataclass
from typing import List, Sequence, Set, Tuple


@dataclass(frozen=True)
class Segment:
    text: str
    kind: str  # "word" | "punct" | "space"


def _is_word_char(ch: str) -> bool:
    return ch.isalnum() or ch in {"'", "’", "_"}


class Segmenter:
    def __init__(self, alphabet: Set[str]):
        self._alphabet = alphabet

    def segments(self, text: str) -> List[Segment]:
        segs: List[Segment] = []
        buf: List[str] = []
        buf_is_word = False

        def flush() -> None:
            nonlocal buf, buf_is_word
            if not buf:
                return
            s = "".join(buf)
            segs.append(Segment(text=s, kind="word" if buf_is_word else "punct"))
            buf = []

        for ch in text:
            if ch not in self._alphabet:
                continue
            if ch.isspace():
                flush()
                segs.append(Segment(text=ch, kind="space"))
                continue

            ch_is_word = _is_word_char(ch)
            if not buf:
                buf.append(ch)
                buf_is_word = ch_is_word
                continue

            if ch_is_word == buf_is_word:
                buf.append(ch)
            else:
                flush()
                buf.append(ch)
                buf_is_word = ch_is_word

        flush()
        return segs

    def tokens(self, text: str) -> List[str]:
        toks: List[str] = []
        for s in self.segments(text):
            if s.kind != "word":
                continue
            t = s.text.strip()
            if not t:
                continue
            toks.append(t)
        return toks


def lower_tokens(tokens: Sequence[str]) -> List[str]:
    return [t.lower() for t in tokens]


def contains_phrase(lower_text: str, phrase: str) -> bool:
    # Phrase match bounded by non-alnum to reduce false positives.
    p = phrase.lower()
    if not p:
        return False
    idx = lower_text.find(p)
    if idx < 0:
        return False
    before_ok = idx == 0 or not lower_text[idx - 1].isalnum()
    after_idx = idx + len(p)
    after_ok = after_idx >= len(lower_text) or not lower_text[after_idx].isalnum()
    return before_ok and after_ok


def ngrams(tokens: Sequence[str], n: int) -> List[Tuple[str, ...]]:
    if n <= 0:
        return []
    if len(tokens) < n:
        return []
    return [tuple(tokens[i : i + n]) for i in range(0, len(tokens) - n + 1)]

