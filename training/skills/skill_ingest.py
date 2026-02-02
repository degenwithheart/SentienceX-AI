from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Dict, List

from locale_pack.loader import LocalePack
from nlp.normalizer import Normalizer
from training.skills.action_extractor import extract_actions


def _root() -> Path:
    return Path(__file__).resolve().parents[2]


def ingest_skills(locale: LocalePack, train_dir: Path) -> Dict[str, object]:
    folder = train_dir / "skills"
    normalizer = Normalizer.from_rule_lines(locale.normalize_rules)
    out_dir = _root() / "knowledge" / "actions"
    out_dir.mkdir(parents=True, exist_ok=True)

    topics = 0
    actions_total = 0
    exported: List[str] = []

    if folder.exists():
        for p in sorted(folder.glob("*.txt")):
            topic = p.stem.strip().lower()
            txt = normalizer.apply(p.read_text(encoding="utf-8", errors="ignore"))
            acts = extract_actions(txt)
            if not acts:
                continue
            topics += 1
            actions_total += len(acts)
            out_path = out_dir / f"{topic}.json"
            out_path.write_text(json.dumps({"version": 1, "topic": topic, "actions": acts, "source": str(p)}, ensure_ascii=False), encoding="utf-8")
            exported.append(f"knowledge/actions/{topic}.json")

    return {"topics": topics, "actions": actions_total, "exported": exported}

