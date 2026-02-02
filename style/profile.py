from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict


def _ema(prev: float, x: float, alpha: float) -> float:
    return (1 - alpha) * prev + alpha * x


@dataclass
class StyleProfile:
    # User style signals (EMA).
    avg_tokens: float = 10.0
    emoji_rate: float = 0.0
    exclaim_rate: float = 0.0
    question_rate: float = 0.0
    hedging_rate: float = 0.0
    directness: float = 0.5  # 0 hedged, 1 direct

    def update(self, tokens: int, emojis: int, exclaims: int, questions: int, hedges: int) -> None:
        self.avg_tokens = _ema(self.avg_tokens, float(tokens), 0.18)
        self.emoji_rate = _ema(self.emoji_rate, float(emojis > 0), 0.10)
        self.exclaim_rate = _ema(self.exclaim_rate, float(exclaims > 0), 0.10)
        self.question_rate = _ema(self.question_rate, float(questions > 0), 0.10)
        self.hedging_rate = _ema(self.hedging_rate, float(hedges > 0), 0.12)
        self.directness = _ema(self.directness, 1.0 - float(hedges > 0), 0.12)

    def to_json(self) -> dict:
        return {
            "avg_tokens": self.avg_tokens,
            "emoji_rate": self.emoji_rate,
            "exclaim_rate": self.exclaim_rate,
            "question_rate": self.question_rate,
            "hedging_rate": self.hedging_rate,
            "directness": self.directness,
        }

    @staticmethod
    def from_json(obj: dict) -> "StyleProfile":
        sp = StyleProfile()
        sp.avg_tokens = float(obj.get("avg_tokens", sp.avg_tokens))
        sp.emoji_rate = float(obj.get("emoji_rate", sp.emoji_rate))
        sp.exclaim_rate = float(obj.get("exclaim_rate", sp.exclaim_rate))
        sp.question_rate = float(obj.get("question_rate", sp.question_rate))
        sp.hedging_rate = float(obj.get("hedging_rate", sp.hedging_rate))
        sp.directness = float(obj.get("directness", sp.directness))
        return sp


def load_style(path: Path) -> StyleProfile:
    if not path.exists():
        return StyleProfile()
    return StyleProfile.from_json(json.loads(path.read_text(encoding="utf-8")))


def save_style(path: Path, style: StyleProfile) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(style.to_json(), ensure_ascii=False), encoding="utf-8")

