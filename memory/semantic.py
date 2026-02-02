from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional

from cognition.contradiction import Claim


def _ema(prev: float, x: float, alpha: float) -> float:
    return (1 - alpha) * prev + alpha * x


@dataclass
class SemanticMemory:
    facts: List[Claim] = field(default_factory=list)
    fact_last_seen: Dict[str, float] = field(default_factory=dict)
    topics: Dict[str, float] = field(default_factory=dict)  # salience
    emotions: Dict[str, float] = field(default_factory=lambda: {"distress": 0.0})
    unresolved: Dict[str, float] = field(default_factory=dict)  # topic->ts first seen
    last_turn_ts: float = 0.0

    def update_facts(self, claims: List[Claim], now: float) -> None:
        for c in claims:
            key = f"{c.key}:{c.value}"
            self.fact_last_seen[key] = now
            # Replace existing (same key/value) with higher confidence, keep polarity.
            replaced = False
            for i, kf in enumerate(self.facts):
                if kf.key == c.key and kf.value == c.value:
                    conf = max(kf.confidence, c.confidence)
                    self.facts[i] = Claim(key=kf.key, value=kf.value, polarity=c.polarity, confidence=conf)
                    replaced = True
                    break
            if not replaced:
                self.facts.append(c)

        # Drop very old, low-confidence facts.
        keep: List[Claim] = []
        for c in self.facts:
            k = f"{c.key}:{c.value}"
            age_days = (now - self.fact_last_seen.get(k, now)) / 86400.0
            if c.confidence >= 0.55:
                keep.append(c)
            elif age_days < 60:
                keep.append(c)
        self.facts = keep

    def update_topics(self, topic_counts: Dict[str, float], now: float) -> None:
        for topic, inc in topic_counts.items():
            self.topics[topic] = _ema(self.topics.get(topic, 0.0), min(1.0, inc), 0.18)
            if inc >= 0.9 and topic not in self.unresolved:
                self.unresolved[topic] = now
        # Gentle decay
        for topic in list(self.topics.keys()):
            self.topics[topic] *= 0.995
            if self.topics[topic] < 0.02:
                self.topics.pop(topic, None)

    def update_emotions(self, distress_score: float) -> None:
        self.emotions["distress"] = _ema(self.emotions.get("distress", 0.0), distress_score, 0.12)

    def mark_resolved(self, topic: str) -> None:
        self.unresolved.pop(topic, None)

    def to_json(self) -> dict:
        return {
            "facts": [c.__dict__ for c in self.facts],
            "fact_last_seen": self.fact_last_seen,
            "topics": self.topics,
            "emotions": self.emotions,
            "unresolved": self.unresolved,
            "last_turn_ts": self.last_turn_ts,
        }

    @staticmethod
    def from_json(obj: dict) -> "SemanticMemory":
        sm = SemanticMemory()
        sm.facts = [Claim(**c) for c in obj.get("facts", [])]
        sm.fact_last_seen = {k: float(v) for k, v in obj.get("fact_last_seen", {}).items()}
        sm.topics = {k: float(v) for k, v in obj.get("topics", {}).items()}
        sm.emotions = {k: float(v) for k, v in obj.get("emotions", {}).items()}
        sm.unresolved = {k: float(v) for k, v in obj.get("unresolved", {}).items()}
        sm.last_turn_ts = float(obj.get("last_turn_ts", 0.0))
        return sm

    def save(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(self.to_json(), ensure_ascii=False), encoding="utf-8")

    @staticmethod
    def load(path: Path) -> "SemanticMemory":
        if not path.exists():
            return SemanticMemory()
        return SemanticMemory.from_json(json.loads(path.read_text(encoding="utf-8")))

