from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict

from locale_pack.loader import LocalePack
from nlp.features import extract_features
from nlp.linear_model import LinearClassifier
from nlp.segmenter import contains_phrase


@dataclass(frozen=True)
class ThreatResult:
    label: str  # none|threat|self_harm
    confidence: float
    probs: Dict[str, float]
    rule_hit: bool


class ThreatModel:
    def __init__(self, clf: LinearClassifier):
        self._clf = clf

    @staticmethod
    def load(models_dir: Path) -> "ThreatModel":
        return ThreatModel(LinearClassifier.load(models_dir / "threat_weights.json"))

    def infer(self, locale: LocalePack, text: str) -> ThreatResult:
        tl = text.lower()
        rule_self = any(contains_phrase(tl, p) for p in ("kill myself", "end my life", "i want to die", "hurt myself"))
        rule_threat = any(contains_phrase(tl, p) for p in ("kill you", "hurt you", "shoot", "stab", "attack"))
        rule_hit = rule_self or rule_threat

        feats = extract_features(locale, text)
        label, conf, probs = self._clf.predict(feats)

        # Force label if high-salience rule patterns present.
        if rule_self:
            label = "self_harm"
            conf = max(conf, 0.90)
        elif rule_threat:
            label = "threat"
            conf = max(conf, 0.85)

        return ThreatResult(label=label, confidence=conf, probs=probs, rule_hit=rule_hit)

