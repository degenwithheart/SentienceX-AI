from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict

from locale_pack.loader import LocalePack
from nlp.features import extract_features
from nlp.linear_model import LinearClassifier


@dataclass(frozen=True)
class IntentResult:
    label: str
    confidence: float
    probs: Dict[str, float]


class IntentModel:
    def __init__(self, clf: LinearClassifier):
        self._clf = clf

    @staticmethod
    def load(models_dir: Path) -> "IntentModel":
        return IntentModel(LinearClassifier.load(models_dir / "intent_weights.json"))

    def infer(self, locale: LocalePack, text: str) -> IntentResult:
        feats = extract_features(locale, text)
        label, conf, probs = self._clf.predict(feats)
        return IntentResult(label=label, confidence=conf, probs=probs)

