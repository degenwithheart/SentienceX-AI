from __future__ import annotations

import json
import random
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Iterable, List, Optional


@dataclass
class BetaArm:
    a: float = 1.0
    b: float = 1.0

    def sample(self, rng: random.Random) -> float:
        return rng.betavariate(self.a, self.b)

    def update(self, success: bool, weight: float = 1.0) -> None:
        if success:
            self.a += float(weight)
        else:
            self.b += float(weight)


@dataclass
class TemplateRanker:
    arms: Dict[str, BetaArm] = field(default_factory=dict)

    def ensure(self, template_ids: Iterable[str]) -> None:
        for tid in template_ids:
            self.arms.setdefault(tid, BetaArm())

    def pick(self, template_ids: List[str], seed: int) -> str:
        self.ensure(template_ids)
        rng = random.Random(seed)
        best_tid = template_ids[0]
        best = -1.0
        for tid in template_ids:
            s = self.arms[tid].sample(rng)
            if s > best:
                best = s
                best_tid = tid
        return best_tid

    def update(self, template_id: str, success: bool, weight: float = 1.0) -> None:
        self.arms.setdefault(template_id, BetaArm()).update(success=success, weight=weight)

    def to_json(self) -> dict:
        return {"arms": {k: {"a": v.a, "b": v.b} for k, v in self.arms.items()}}

    @staticmethod
    def from_json(obj: dict) -> "TemplateRanker":
        tr = TemplateRanker()
        for k, v in obj.get("arms", {}).items():
            tr.arms[k] = BetaArm(a=float(v.get("a", 1.0)), b=float(v.get("b", 1.0)))
        return tr


def load_ranker(path: Path) -> TemplateRanker:
    if not path.exists():
        return TemplateRanker()
    return TemplateRanker.from_json(json.loads(path.read_text(encoding="utf-8")))


def save_ranker(path: Path, ranker: TemplateRanker) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(ranker.to_json(), ensure_ascii=False), encoding="utf-8")

