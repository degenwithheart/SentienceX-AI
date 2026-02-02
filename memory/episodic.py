from __future__ import annotations

import json
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional

from locale_pack.loader import LocalePack
from nlp.segmenter import Segmenter


@dataclass(frozen=True)
class Episode:
    episode_id: int
    started_at: float
    ended_at: float
    summary: str
    top_terms: List[str]
    distress_avg: float


class EpisodicMemory:
    def __init__(self, path: Path, locale: LocalePack):
        self._path = path
        self._locale = locale
        self._episodes: List[Episode] = []
        self._next_id = 1
        self._load()

    def _load(self) -> None:
        if not self._path.exists():
            return
        for ln in self._path.read_text(encoding="utf-8").splitlines():
            if not ln.strip():
                continue
            obj = json.loads(ln)
            ep = Episode(
                episode_id=int(obj["episode_id"]),
                started_at=float(obj["started_at"]),
                ended_at=float(obj["ended_at"]),
                summary=str(obj["summary"]),
                top_terms=list(obj.get("top_terms", [])),
                distress_avg=float(obj.get("distress_avg", 0.0)),
            )
            self._episodes.append(ep)
            self._next_id = max(self._next_id, ep.episode_id + 1)

    def add(self, started_at: float, ended_at: float, turns: List[str], distress_scores: List[float]) -> Episode:
        seg = Segmenter(self._locale.alphabet)
        counts: Dict[str, int] = {}
        for t in turns:
            for tok in seg.tokens(t):
                tl = tok.lower().strip("._-,'\"!?()[]{}<>:;")
                if len(tl) < 4:
                    continue
                counts[tl] = counts.get(tl, 0) + 1
        top_terms = [w for w, _ in sorted(counts.items(), key=lambda kv: kv[1], reverse=True)[:8]]
        distress_avg = sum(distress_scores) / max(1, len(distress_scores))

        if distress_avg >= 0.65:
            summary = f"Heavy episode touching {', '.join(top_terms[:3])}."
        elif distress_avg >= 0.40:
            summary = f"Mixed episode around {', '.join(top_terms[:3])}."
        else:
            summary = f"Light episode about {', '.join(top_terms[:3])}."

        ep = Episode(
            episode_id=self._next_id,
            started_at=started_at,
            ended_at=ended_at,
            summary=summary,
            top_terms=top_terms,
            distress_avg=float(distress_avg),
        )
        self._next_id += 1
        self._episodes.append(ep)

        self._path.parent.mkdir(parents=True, exist_ok=True)
        with self._path.open("a", encoding="utf-8") as f:
            f.write(
                json.dumps(
                    {
                        "episode_id": ep.episode_id,
                        "started_at": ep.started_at,
                        "ended_at": ep.ended_at,
                        "summary": ep.summary,
                        "top_terms": ep.top_terms,
                        "distress_avg": ep.distress_avg,
                    },
                    ensure_ascii=False,
                )
                + "\n"
            )
        return ep

    def recent(self, n: int = 8) -> List[Episode]:
        return list(self._episodes)[-n:]

    def all(self) -> List[Episode]:
        return list(self._episodes)

