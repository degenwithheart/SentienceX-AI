from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, Iterator, List, Tuple

from cognition.hidden_emotion import infer_hidden_distress
from cognition.masking_detector import detect_masking
from locale_pack.loader import LocalePack
from nlp.intent import IntentModel
from nlp.sarcasm import SarcasmModel
from nlp.sentiment import SentimentModel
from nlp.threat import ThreatModel
from nlp.normalizer import Normalizer
from nlp.sentence_splitter import SentenceSplitter


def _root() -> Path:
    return Path(__file__).resolve().parents[2]


def _walk_txt(folder: Path) -> Iterator[Path]:
    if not folder.exists():
        return iter(())
    for root, _, fns in os.walk(folder):
        for fn in sorted(fns):
            if fn.startswith("."):
                continue
            p = Path(root) / fn
            if p.suffix.lower() not in {".txt", ".md"}:
                continue
            yield p


@dataclass(frozen=True)
class StorySentence:
    text: str
    sentiment: str
    distress: float
    masking: float


def _state(sentiment: str, distress: float, masking: float) -> str:
    if distress >= 0.72:
        return "distress"
    if masking >= 0.70 and distress >= 0.55:
        return "masked_distress"
    return sentiment


def ingest_stories(locale: LocalePack, folder: Path) -> Iterator[Tuple[Path, List[str]]]:
    normalizer = Normalizer.from_rule_lines(locale.normalize_rules)
    splitter = SentenceSplitter(locale.abbreviations)

    for p in _walk_txt(folder):
        txt = p.read_text(encoding="utf-8", errors="ignore").strip()
        if not txt:
            continue
        txt = normalizer.apply(txt)
        sents = [s.text for s in splitter.split(txt)]
        if not sents:
            sents = [txt]
        yield p, sents


def run_story_mining(locale: LocalePack, train_dir: Path) -> Dict[str, object]:
    folder = train_dir / "stories"
    root = _root()
    out_dir = root / "cognition"
    out_dir.mkdir(parents=True, exist_ok=True)

    sentiment_m = SentimentModel.load(root / "models")

    transitions: Dict[str, Dict[str, int]] = {}
    cond_mask_distress = {"masking_and_distress": 0, "masking_total": 0}
    cond_short_after_distress = {"short_after": 0, "after_total": 0}

    doc_count = 0
    sent_count = 0

    for _, sents in ingest_stories(locale, folder):
        doc_count += 1
        seq: List[StorySentence] = []
        prev_was_distress = False
        for s in sents:
            sent_count += 1
            sr = sentiment_m.infer(locale, s)
            hidden = infer_hidden_distress(locale, s)
            masking = detect_masking(locale, s)
            seq.append(StorySentence(text=s, sentiment=sr.label, distress=hidden.distress_score, masking=masking.confidence))

            if masking.is_masking:
                cond_mask_distress["masking_total"] += 1
                if hidden.distress_score >= 0.62:
                    cond_mask_distress["masking_and_distress"] += 1

            if prev_was_distress:
                cond_short_after_distress["after_total"] += 1
                if len(s) <= 28:
                    cond_short_after_distress["short_after"] += 1
            prev_was_distress = hidden.distress_score >= 0.72

        for a, b in zip(seq, seq[1:]):
            sa = _state(a.sentiment, a.distress, a.masking)
            sb = _state(b.sentiment, b.distress, b.masking)
            transitions.setdefault(sa, {}).setdefault(sb, 0)
            transitions[sa][sb] += 1

    # Convert counts to probabilities.
    trans_prob: Dict[str, Dict[str, float]] = {}
    for a, row in transitions.items():
        total = sum(row.values()) or 1
        trans_prob[a] = {b: v / total for b, v in row.items()}

    p_masked_distress = 0.0
    if cond_mask_distress["masking_total"] > 0:
        p_masked_distress = cond_mask_distress["masking_and_distress"] / cond_mask_distress["masking_total"]

    p_withdraw_after = 0.0
    if cond_short_after_distress["after_total"] > 0:
        p_withdraw_after = cond_short_after_distress["short_after"] / cond_short_after_distress["after_total"]

    hidden_priors = {
        "version": 1,
        "source": "TRAIN/stories",
        "doc_count": doc_count,
        "sentence_count": sent_count,
        "transition_prob": trans_prob,
        "p_hidden_distress_given_masking": p_masked_distress,
    }
    (out_dir / "hidden_emotion_priors.json").write_text(json.dumps(hidden_priors, ensure_ascii=False), encoding="utf-8")

    masking_priors = {
        "version": 1,
        "source": "TRAIN/stories",
        "doc_count": doc_count,
        "p_short_sentence_after_distress": p_withdraw_after,
        "p_hidden_distress_given_masking": p_masked_distress,
    }
    (out_dir / "masking_patterns.json").write_text(json.dumps(masking_priors, ensure_ascii=False), encoding="utf-8")

    social = {
        "version": 1,
        "source": "TRAIN/stories",
        "p_short_sentence_after_distress": p_withdraw_after,
        "short_len_chars": 28,
    }
    (out_dir / "social_withdrawal.json").write_text(json.dumps(social, ensure_ascii=False), encoding="utf-8")

    return {
        "docs": doc_count,
        "sentences": sent_count,
        "exported": [
            "cognition/hidden_emotion_priors.json",
            "cognition/masking_patterns.json",
            "cognition/social_withdrawal.json",
        ],
        "p_hidden_distress_given_masking": p_masked_distress,
        "p_short_sentence_after_distress": p_withdraw_after,
    }

