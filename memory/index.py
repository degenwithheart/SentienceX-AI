from __future__ import annotations

import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Set, Tuple

from nlp.segmenter import Segmenter


_STOP = {
    "the",
    "a",
    "an",
    "and",
    "or",
    "but",
    "to",
    "of",
    "in",
    "on",
    "for",
    "with",
    "at",
    "by",
    "from",
    "is",
    "are",
    "was",
    "were",
    "be",
    "been",
    "it",
    "that",
    "this",
    "i",
    "you",
    "we",
    "they",
    "me",
    "my",
    "your",
    "our",
}


def _terms(seg: Segmenter, text: str) -> Set[str]:
    terms: Set[str] = set()
    for t in seg.tokens(text):
        tl = t.lower()
        tl = tl.strip("._-,'\"!?()[]{}<>:;")
        if len(tl) < 3:
            continue
        if tl in _STOP:
            continue
        if any(ch.isdigit() for ch in tl) and len(tl) > 24:
            continue
        terms.add(tl)
    return terms


@dataclass
class InvertedIndex:
    path: Path
    postings: Dict[str, List[int]]
    doc_freq: Dict[str, int]
    doc_count: int

    @staticmethod
    def open(path: Path) -> "InvertedIndex":
        if path.exists():
            data = json.loads(path.read_text(encoding="utf-8"))
            return InvertedIndex(
                path=path,
                postings={k: list(map(int, v)) for k, v in data.get("postings", {}).items()},
                doc_freq={k: int(v) for k, v in data.get("doc_freq", {}).items()},
                doc_count=int(data.get("doc_count", 0)),
            )
        return InvertedIndex(path=path, postings={}, doc_freq={}, doc_count=0)

    def flush(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(
            json.dumps({"postings": self.postings, "doc_freq": self.doc_freq, "doc_count": self.doc_count}, ensure_ascii=False),
            encoding="utf-8",
        )

    def add_document(self, seg: Segmenter, doc_id: int, text: str) -> None:
        terms = _terms(seg, text)
        if not terms:
            self.doc_count += 1
            return
        for term in terms:
            lst = self.postings.get(term)
            if lst is None:
                self.postings[term] = [doc_id]
            else:
                if not lst or lst[-1] != doc_id:
                    lst.append(doc_id)
            self.doc_freq[term] = self.doc_freq.get(term, 0) + 1
        self.doc_count += 1

    def idf(self, term: str) -> float:
        df = self.doc_freq.get(term, 0)
        return math.log((1.0 + self.doc_count) / (1.0 + df)) + 1.0

    def search(self, seg: Segmenter, query: str, limit: int = 12) -> List[Tuple[int, float]]:
        qterms = _terms(seg, query)
        if not qterms:
            return []
        scores: Dict[int, float] = {}
        for term in qterms:
            postings = self.postings.get(term, [])
            w = self.idf(term)
            for doc_id in postings[-400:]:
                scores[doc_id] = scores.get(doc_id, 0.0) + w
        return sorted(scores.items(), key=lambda kv: kv[1], reverse=True)[:limit]

