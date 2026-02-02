from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional


def _root() -> Path:
    return Path(__file__).resolve().parents[1]


@dataclass(frozen=True)
class TopicProfile:
    topic: str
    related_terms: List[str]
    emotion_associations: Dict[str, float]
    sensitivity_level: float


@dataclass
class KnowledgeStore:
    topics: Dict[str, TopicProfile]
    actions: Dict[str, List[str]]  # topic -> actions

    @staticmethod
    def load() -> "KnowledgeStore":
        root = _root()
        topics_path = root / "knowledge" / "topics.json"
        actions_dir = root / "knowledge" / "actions"

        topics: Dict[str, TopicProfile] = {}
        if topics_path.exists():
            obj = json.loads(topics_path.read_text(encoding="utf-8"))
            for t in obj.get("topics", []):
                tp = TopicProfile(
                    topic=str(t["topic"]),
                    related_terms=list(t.get("related_terms", [])),
                    emotion_associations={k: float(v) for k, v in t.get("emotion_associations", {}).items()},
                    sensitivity_level=float(t.get("sensitivity_level", 0.2)),
                )
                topics[tp.topic] = tp

        actions: Dict[str, List[str]] = {}
        if actions_dir.exists():
            for p in sorted(actions_dir.glob("*.json")):
                try:
                    aobj = json.loads(p.read_text(encoding="utf-8"))
                    topic = str(aobj.get("topic") or p.stem)
                    acts = [str(x).strip() for x in aobj.get("actions", []) if str(x).strip()]
                    if acts:
                        actions[topic] = acts
                except Exception:
                    continue

        return KnowledgeStore(topics=topics, actions=actions)

    def best_actions(self, topic: str, limit: int = 1) -> List[str]:
        if not topic:
            return []
        acts = self.actions.get(topic, [])
        return acts[: max(0, int(limit))]

