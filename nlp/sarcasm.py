from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict

from locale_pack.loader import LocalePack
from nlp.features import extract_features
from nlp.linear_model import LinearClassifier


@dataclass(frozen=True)
class SarcasmResult:
    is_sarcastic: bool
    confidence: float
    probs: Dict[str, float]


class SarcasmModel:
    def __init__(self, clf: LinearClassifier):
        self._clf = clf

    @staticmethod
    def load(models_dir: Path) -> "SarcasmModel":
        return SarcasmModel(LinearClassifier.load(models_dir / "sarcasm_weights.json"))

    def infer(self, locale: LocalePack, text: str) -> SarcasmResult:
        feats = extract_features(locale, text)
        label, conf, probs = self._clf.predict(feats)
        return SarcasmResult(is_sarcastic=(label == "sarcastic"), confidence=conf, probs=probs)

