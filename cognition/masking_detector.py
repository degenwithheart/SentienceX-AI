from __future__ import annotations

from dataclasses import dataclass

from locale_pack.loader import LocalePack
from nlp.features import extract_features
from cognition.learned import masking_patterns


@dataclass(frozen=True)
class MaskingResult:
    is_masking: bool
    confidence: float
    reasons: list[str]


def detect_masking(locale: LocalePack, text: str) -> MaskingResult:
    feats = extract_features(locale, text)
    reasons: list[str] = []

    masking = feats.get("masking_hits", 0.0)
    minim = feats.get("minimizer_hits", 0.0)
    hedge = feats.get("hedging_hits", 0.0)
    neg = feats.get("neg_hits", 0.0)
    distress = feats.get("distress_hits", 0.0)

    score = 0.0
    if masking > 0:
        score += min(0.60, 0.25 + 0.15 * masking)
        reasons.append("masking_markers")
    if minim > 0:
        score += min(0.22, 0.10 * minim)
        reasons.append("minimizers")
    if hedge > 0:
        score += min(0.15, 0.07 * hedge)
        reasons.append("hedging")
    if neg > 0 or distress > 0:
        score += 0.10
        reasons.append("negative_context")

    pri = masking_patterns()
    if pri is not None:
        try:
            p = float(pri.get("p_hidden_distress_given_masking", 0.0))
            if masking > 0 and p >= 0.60:
                score += 0.06
                reasons.append("learned_masking_pattern")
        except Exception:
            pass

    score = max(0.0, min(1.0, score))
    return MaskingResult(is_masking=score >= 0.55, confidence=score, reasons=sorted(set(reasons)))
