from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict

from locale_pack.loader import LocalePack
from nlp.features import extract_features
from nlp.linear_model import LinearClassifier


@dataclass(frozen=True)
class SentimentResult:
    label: str  # pos|neu|neg
    confidence: float
    score: float
    probs: Dict[str, float]


class SentimentModel:
    def __init__(self, clf: LinearClassifier):
        self._clf = clf

    @staticmethod
    def load(models_dir: Path) -> "SentimentModel":
        return SentimentModel(LinearClassifier.load(models_dir / "sentiment_weights.json"))

    def infer(self, locale: LocalePack, text: str) -> SentimentResult:
        feats = extract_features(locale, text)
        label, conf, probs = self._clf.predict(feats)
        # Continuous score: pos - neg plus model bias
        score = (probs.get("pos", 0.0) - probs.get("neg", 0.0)) * 2.0
        return SentimentResult(label=label, confidence=conf, score=score, probs=probs)

