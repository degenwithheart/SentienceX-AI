from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List


def _ema(prev: float, x: float, alpha: float) -> float:
    return (1 - alpha) * prev + alpha * x


@dataclass
class TonePreference:
    # Higher means "more preferred".
    scores: Dict[str, float] = field(default_factory=lambda: {"normal": 0.0, "empathy": 0.0, "ack_short": 0.0, "proactive": 0.0, "safety": 0.0})

    def update(self, tone: str, reward: float) -> None:
        self.scores[tone] = _ema(self.scores.get(tone, 0.0), float(reward), 0.12)

    def adjust(self, base: Dict[str, float]) -> Dict[str, float]:
        # Add a small bias in logit-space-ish.
        out: Dict[str, float] = dict(base)
        for tone, pref in self.scores.items():
            out[tone] = out.get(tone, 0.0) + 0.35 * pref
        return out

    def to_json(self) -> dict:
        return {"scores": self.scores}

    @staticmethod
    def from_json(obj: dict) -> "TonePreference":
        tp = TonePreference()
        tp.scores = {k: float(v) for k, v in obj.get("scores", {}).items()}
        return tp


def load_tone(path: Path) -> TonePreference:
    if not path.exists():
        return TonePreference()
    return TonePreference.from_json(json.loads(path.read_text(encoding="utf-8")))


def save_tone(path: Path, tone: TonePreference) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(tone.to_json(), ensure_ascii=False), encoding="utf-8")

