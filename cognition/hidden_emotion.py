from __future__ import annotations

from dataclasses import dataclass

from locale_pack.loader import LocalePack
from nlp.features import extract_features
from cognition.learned import hidden_priors


@dataclass(frozen=True)
class HiddenEmotion:
    distress_score: float  # 0..1
    reasons: list[str]


def infer_hidden_distress(locale: LocalePack, text: str) -> HiddenEmotion:
    feats = extract_features(locale, text)
    reasons: list[str] = []

    pos = feats.get("pos_hits", 0.0)
    neg = feats.get("neg_hits", 0.0)
    distress = feats.get("distress_hits", 0.0)
    masking = feats.get("masking_hits", 0.0)
    minim = feats.get("minimizer_hits", 0.0)
    hedge = feats.get("hedging_hits", 0.0)
    ell = feats.get("ellipses", 0.0)

    score = 0.0

    # Topic-driven: distress topics are strong.
    if distress > 0:
        score += min(0.55, 0.18 * distress + 0.25)
        reasons.append("distress_topic")

    # Surface-positive but context-negative mismatch.
    if pos > 0 and (neg > 0 or distress > 0):
        score += 0.18
        reasons.append("positive_negative_mismatch")

    # Emotional masking markers often appear with avoidance / minimization.
    if masking > 0:
        score += min(0.22, 0.12 * masking)
        reasons.append("masking_markers")

    if minim > 0:
        score += min(0.18, 0.10 * minim)
        reasons.append("minimization")

    if hedge > 0:
        score += min(0.12, 0.06 * hedge)
        reasons.append("hedging")

    if ell > 0:
        score += min(0.10, 0.06 * ell)
        reasons.append("ellipsis_hesitation")

    # Explicit negativity still matters.
    if neg > 0:
        score += min(0.25, 0.08 * neg)
        reasons.append("negative_words")

    # Learned priors can slightly adjust the masking->distress link without changing core logic.
    pri = hidden_priors()
    if pri is not None and masking > 0:
        try:
            p = float(pri.get("p_hidden_distress_given_masking", 0.0))
            # If the corpus says masking often hides distress, boost; otherwise don't.
            boost = (p - 0.45) * 0.35
            if boost > 0:
                score += min(0.12, boost)
                reasons.append("learned_masking_prior")
        except Exception:
            pass

    score = max(0.0, min(1.0, score))
    return HiddenEmotion(distress_score=score, reasons=sorted(set(reasons)))
