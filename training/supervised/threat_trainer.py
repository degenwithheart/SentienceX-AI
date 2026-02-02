from __future__ import annotations

import time
from pathlib import Path
from typing import Dict

from locale_pack.loader import LocalePack
from nlp.features import extract_features
from training.state import TrainingState
from training.supervised.dataset import labels_in_folder, stream_samples
from training.supervised.linear_sgd import SGDConfig, SoftmaxSGD, load_or_init, save_model


def train_threat(locale: LocalePack, train_dir: Path, data_dir: Path, state: TrainingState, force_full: bool = False) -> Dict[str, object]:
    t0 = time.time()
    folder = train_dir / "threat"
    weak = data_dir / "weak_labels" / "threat"
    labels = labels_in_folder(folder) or ["none", "threat", "self_harm"]
    model_path = Path(__file__).resolve().parents[2] / "models" / "threat_weights.json"

    w = load_or_init(model_path, labels=labels)
    sgd = SoftmaxSGD(w, SGDConfig(lr0=0.16, l2=1.4e-4))

    seen = 0
    for samp in stream_samples(locale, folder, state, force_full=force_full):
        feats = extract_features(locale, samp.text)
        sgd.update(feats, gold=samp.label, weight=1.0)
        seen += 1
    for samp in stream_samples(locale, weak, state, force_full=force_full):
        feats = extract_features(locale, samp.text)
        sgd.update(feats, gold=samp.label, weight=0.40)
        seen += 1

    if seen > 0:
        save_model(model_path, sgd.w)
    return {"samples": seen, "labels": labels, "steps": sgd.steps, "saved": bool(seen > 0), "seconds": time.time() - t0}

