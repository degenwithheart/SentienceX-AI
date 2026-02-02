from __future__ import annotations

import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Tuple


@dataclass(frozen=True)
class LinearWeights:
    bias: float
    weights: Dict[str, float]

    def score(self, feats: Dict[str, float]) -> float:
        s = self.bias
        for k, v in feats.items():
            w = self.weights.get(k)
            if w is not None:
                s += w * v
        return s


def softmax(scores: Dict[str, float]) -> Dict[str, float]:
    if not scores:
        return {}
    mx = max(scores.values())
    exps = {k: math.exp(v - mx) for k, v in scores.items()}
    z = sum(exps.values()) or 1.0
    return {k: v / z for k, v in exps.items()}


class LinearClassifier:
    def __init__(self, label_weights: Dict[str, LinearWeights]):
        self._lw = label_weights

    @staticmethod
    def load(path: Path) -> "LinearClassifier":
        data = json.loads(path.read_text(encoding="utf-8"))
        if "labels" not in data:
            raise ValueError(f"{path} missing 'labels'")
        lw: Dict[str, LinearWeights] = {}
        for label, obj in data["labels"].items():
            lw[label] = LinearWeights(bias=float(obj.get("bias", 0.0)), weights={k: float(v) for k, v in obj["weights"].items()})
        return LinearClassifier(lw)

    def predict(self, feats: Dict[str, float]) -> Tuple[str, float, Dict[str, float]]:
        scores = {label: w.score(feats) for label, w in self._lw.items()}
        probs = softmax(scores)
        if not probs:
            return "unknown", 0.0, {}
        label = max(probs, key=probs.get)
        return label, float(probs[label]), probs

