from __future__ import annotations

import json
import math
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Tuple


def _clip(x: float, lo: float, hi: float) -> float:
    return lo if x < lo else hi if x > hi else x


def _softmax(scores: Dict[str, float]) -> Dict[str, float]:
    if not scores:
        return {}
    mx = max(scores.values())
    exps = {k: math.exp(v - mx) for k, v in scores.items()}
    z = sum(exps.values()) or 1.0
    return {k: v / z for k, v in exps.items()}


@dataclass
class SoftmaxWeights:
    labels: List[str]
    bias: Dict[str, float]
    weights: Dict[str, Dict[str, float]]  # label -> feature -> weight

    @staticmethod
    def from_model_json(obj: dict) -> "SoftmaxWeights":
        labels = sorted(obj.get("labels", {}).keys())
        bias: Dict[str, float] = {}
        weights: Dict[str, Dict[str, float]] = {}
        for lab in labels:
            lobj = obj["labels"][lab]
            bias[lab] = float(lobj.get("bias", 0.0))
            weights[lab] = {k: float(v) for k, v in lobj.get("weights", {}).items()}
        return SoftmaxWeights(labels=labels, bias=bias, weights=weights)

    def to_model_json(self) -> dict:
        return {"labels": {lab: {"bias": self.bias.get(lab, 0.0), "weights": self.weights.get(lab, {})} for lab in self.labels}}

    def score(self, feats: Dict[str, float]) -> Dict[str, float]:
        scores: Dict[str, float] = {}
        for lab in self.labels:
            s = self.bias.get(lab, 0.0)
            w = self.weights.get(lab, {})
            for k, v in feats.items():
                wk = w.get(k)
                if wk is not None:
                    s += wk * v
            scores[lab] = s
        return scores

    def predict(self, feats: Dict[str, float]) -> Tuple[str, float, Dict[str, float]]:
        probs = _softmax(self.score(feats))
        if not probs:
            return "unknown", 0.0, {}
        lab = max(probs, key=probs.get)
        return lab, float(probs[lab]), probs


@dataclass
class SGDConfig:
    lr0: float = 0.25
    l2: float = 1e-4
    min_lr: float = 0.03
    max_grad: float = 3.0
    prune_every: int = 3000
    prune_abs: float = 1e-4


class SoftmaxSGD:
    def __init__(self, w: SoftmaxWeights, cfg: SGDConfig):
        self.w = w
        self.cfg = cfg
        self.steps = 0

    def _lr(self) -> float:
        # Simple inverse-time decay.
        lr = self.cfg.lr0 / math.sqrt(1.0 + self.steps / 2500.0)
        return max(self.cfg.min_lr, float(lr))

    def update(self, feats: Dict[str, float], gold: str, weight: float = 1.0) -> Dict[str, float]:
        self.steps += 1
        lr = self._lr()
        scores = self.w.score(feats)
        probs = _softmax(scores)

        # Dense gradient only over labels; feature updates are sparse.
        for lab in self.w.labels:
            y = 1.0 if lab == gold else 0.0
            p = probs.get(lab, 0.0)
            g = (p - y) * float(weight)
            g = _clip(g, -self.cfg.max_grad, self.cfg.max_grad)

            # Bias update with L2.
            b = self.w.bias.get(lab, 0.0)
            b -= lr * (g + self.cfg.l2 * b)
            self.w.bias[lab] = b

            # Feature updates
            wlab = self.w.weights.setdefault(lab, {})
            for k, x in feats.items():
                wk = wlab.get(k, 0.0)
                wk -= lr * (g * x + self.cfg.l2 * wk)
                if abs(wk) < self.cfg.prune_abs and self.steps % self.cfg.prune_every == 0:
                    wlab.pop(k, None)
                else:
                    wlab[k] = wk

        if self.steps % self.cfg.prune_every == 0:
            self.prune()
        return probs

    def prune(self) -> None:
        thr = float(self.cfg.prune_abs)
        for lab in self.w.labels:
            wlab = self.w.weights.get(lab, {})
            kill = [k for k, v in wlab.items() if abs(v) < thr]
            for k in kill:
                wlab.pop(k, None)


def load_or_init(path: Path, labels: List[str]) -> SoftmaxWeights:
    if path.exists():
        obj = json.loads(path.read_text(encoding="utf-8"))
        w = SoftmaxWeights.from_model_json(obj)
        # Ensure label set stable; add missing with zero weights.
        for lab in labels:
            if lab not in w.labels:
                w.labels.append(lab)
                w.bias[lab] = 0.0
                w.weights[lab] = {}
        w.labels = sorted(set(w.labels))
        return w
    return SoftmaxWeights(labels=sorted(labels), bias={lab: 0.0 for lab in labels}, weights={lab: {} for lab in labels})


def save_model(path: Path, w: SoftmaxWeights) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(w.to_model_json(), ensure_ascii=False), encoding="utf-8")

