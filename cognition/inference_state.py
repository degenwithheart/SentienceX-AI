from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Optional

from cognition.contradiction import Claim, ContradictionResult, contradiction_score, extract_claims
from cognition.hidden_emotion import HiddenEmotion, infer_hidden_distress
from cognition.masking_detector import MaskingResult, detect_masking
from locale_pack.loader import LocalePack
from nlp.normalizer import Normalizer
from nlp.sarcasm import SarcasmModel, SarcasmResult
from nlp.sentiment import SentimentModel, SentimentResult
from nlp.sentence_splitter import SentenceSplitter
from nlp.threat import ThreatModel, ThreatResult
from nlp.intent import IntentModel, IntentResult


def _models_dir() -> Path:
    return Path(__file__).resolve().parents[1] / "models"


_CACHED: Dict[str, object] = {}
_MTIMES: Dict[str, float] = {}


def _models_mtime(md: Path) -> float:
    mt = 0.0
    for fn in ("sentiment_weights.json", "intent_weights.json", "sarcasm_weights.json", "threat_weights.json"):
        p = md / fn
        if p.exists():
            mt = max(mt, p.stat().st_mtime)
    return mt


def _get_models() -> tuple[SentimentModel, IntentModel, SarcasmModel, ThreatModel]:
    key = "models.v1"
    md = _models_dir()
    mt = _models_mtime(md)
    if key in _CACHED and _MTIMES.get(key) == mt:
        return _CACHED[key]  # type: ignore[return-value]
    models = (
        SentimentModel.load(md),
        IntentModel.load(md),
        SarcasmModel.load(md),
        ThreatModel.load(md),
    )
    _CACHED[key] = models
    _MTIMES[key] = mt
    return models


@dataclass(frozen=True)
class InferenceState:
    text: str
    normalized: str
    sentiment: SentimentResult
    intent: IntentResult
    sarcasm: SarcasmResult
    threat: ThreatResult
    masking: MaskingResult
    hidden: HiddenEmotion
    claims: list[Claim]
    contradiction: Optional[ContradictionResult]

    @staticmethod
    def from_text(locale: LocalePack, text: str, known_facts: Optional[list[Claim]] = None) -> "InferenceState":
        normalizer = Normalizer.from_rule_lines(locale.normalize_rules)
        normalized = normalizer.apply(text)

        splitter = SentenceSplitter(locale.abbreviations)
        _ = splitter.split(normalized)  # kept for future features; validates localization logic

        sentiment_m, intent_m, sarcasm_m, threat_m = _get_models()
        sentiment = sentiment_m.infer(locale, normalized)
        intent = intent_m.infer(locale, normalized)
        sarcasm = sarcasm_m.infer(locale, normalized)
        threat = threat_m.infer(locale, normalized)

        masking = detect_masking(locale, normalized)
        hidden = infer_hidden_distress(locale, normalized)
        claims = extract_claims(normalized)

        contradiction = None
        if known_facts:
            contradiction = contradiction_score(claims, known_facts)

        return InferenceState(
            text=text,
            normalized=normalized,
            sentiment=sentiment,
            intent=intent,
            sarcasm=sarcasm,
            threat=threat,
            masking=masking,
            hidden=hidden,
            claims=claims,
            contradiction=contradiction,
        )
