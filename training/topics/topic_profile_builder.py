from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional

from locale_pack.loader import LocalePack


def _root() -> Path:
    return Path(__file__).resolve().parents[2]


def _load_ingest(root: Path) -> List[dict]:
    p = root / "knowledge" / "topics_ingest.json"
    if not p.exists():
        return []
    obj = json.loads(p.read_text(encoding="utf-8"))
    return list(obj.get("topics", []))


def build_topic_profiles(locale: LocalePack, train_dir: Path, topics_ingest: Optional[Dict[str, object]] = None) -> Dict[str, object]:
    root = _root()
    items = _load_ingest(root)
    profiles: List[dict] = []

    pos = locale.lexicons.sentiment_pos
    neg = locale.lexicons.sentiment_neg
    distress = locale.lexicons.distress_topics

    for it in items:
        topic = str(it.get("topic", "")).strip().lower()
        terms = list(it.get("terms", {}).keys())
        sens = float(it.get("sensitivity", 0.2))

        assoc: Dict[str, float] = {"pos": 0.0, "neg": 0.0, "distress": 0.0}
        if terms:
            assoc["pos"] = sum(1.0 for t in terms if t in pos) / len(terms)
            assoc["neg"] = sum(1.0 for t in terms if t in neg) / len(terms)
            assoc["distress"] = sum(1.0 for t in terms if t in distress) / len(terms)

        # Sensitivity adjustments: threat-like topics should be high sensitivity.
        if topic in {"suicide", "self_harm", "self-harm"}:
            sens = max(sens, 0.95)
        if assoc["distress"] >= 0.25:
            sens = max(sens, 0.45)

        profiles.append(
            {
                "topic": topic,
                "related_terms": terms[:64],
                "emotion_associations": assoc,
                "sensitivity_level": max(0.0, min(1.0, sens)),
            }
        )

    out_dir = root / "knowledge"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "topics.json"
    out_path.write_text(json.dumps({"version": 1, "topics": profiles}, ensure_ascii=False), encoding="utf-8")

    return {"topics": len(profiles), "exported": ["knowledge/topics.json"]}

