from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Tuple

from locale_pack.loader import LocalePack
from nlp.normalizer import Normalizer


def _root() -> Path:
    return Path(__file__).resolve().parents[2]


@dataclass(frozen=True)
class TopicIngest:
    topic: str
    terms: Dict[str, float]
    sensitivity: float
    sources: List[str]


def _parse_header(line: str) -> Tuple[str, str]:
    s = line.strip().lstrip("#").strip()
    if "=" in s:
        k, v = s.split("=", 1)
        return k.strip().lower(), v.strip()
    if ":" in s:
        k, v = s.split(":", 1)
        return k.strip().lower(), v.strip()
    return "", ""


def ingest_topics(locale: LocalePack, train_dir: Path) -> Dict[str, object]:
    folder = train_dir / "topics"
    normalizer = Normalizer.from_rule_lines(locale.normalize_rules)

    ingests: List[TopicIngest] = []
    if folder.exists():
        for p in sorted(folder.glob("*.txt")):
            raw = p.read_text(encoding="utf-8", errors="ignore").splitlines()
            topic = p.stem.strip().lower()
            sensitivity = 0.2
            terms: Dict[str, float] = {}
            sources = [str(p)]
            for ln in raw:
                s = ln.strip()
                if not s:
                    continue
                if s.startswith("#"):
                    k, v = _parse_header(s)
                    if k in {"topic", "id"} and v:
                        topic = v.strip().lower()
                    if k in {"sensitivity", "sensitivity_level"}:
                        try:
                            sensitivity = float(v)
                        except Exception:
                            pass
                    continue
                s = normalizer.apply(s)
                if "|" in s:
                    term, w = s.split("|", 1)
                    term = term.strip().lower()
                    try:
                        wt = float(w.strip())
                    except Exception:
                        wt = 1.0
                else:
                    term = s.strip().lower()
                    wt = 1.0
                if term:
                    terms[term] = max(terms.get(term, 0.0), wt)
            if terms:
                ingests.append(TopicIngest(topic=topic, terms=terms, sensitivity=max(0.0, min(1.0, sensitivity)), sources=sources))

    out_dir = _root() / "knowledge"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "topics_ingest.json"
    out_path.write_text(
        json.dumps(
            {
                "version": 1,
                "source": "TRAIN/topics",
                "topics": [{"topic": t.topic, "terms": t.terms, "sensitivity": t.sensitivity, "sources": t.sources} for t in ingests],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    return {"topics": len(ingests), "exported": ["knowledge/topics_ingest.json"]}

