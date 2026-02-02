from __future__ import annotations

import json
from pathlib import Path
from typing import Dict

from locale_pack.loader import LocalePack
from nlp.normalizer import Normalizer
from style.extractor import extract_style
from style.profile import StyleProfile, save_style


def bootstrap_style(locale: LocalePack, train_dir: Path, data_dir: Path) -> Dict[str, object]:
    folder = train_dir / "style_samples"
    p = folder / "user.txt"
    if not p.exists():
        return {"bootstrapped": False, "reason": "TRAIN/style_samples/user.txt not found"}

    normalizer = Normalizer.from_rule_lines(locale.normalize_rules)
    txt = normalizer.apply(p.read_text(encoding="utf-8", errors="ignore"))
    lines = [ln.strip() for ln in txt.splitlines() if ln.strip()]
    if not lines:
        return {"bootstrapped": False, "reason": "no content"}

    sp = StyleProfile()
    for ln in lines[:2000]:
        sig = extract_style(locale, ln)
        sp.update(sig.tokens, sig.emojis, sig.exclaims, sig.questions, sig.hedges)

    out_path = data_dir / "style.json"
    save_style(out_path, sp)
    return {"bootstrapped": True, "samples": min(len(lines), 2000), "exported": [str(out_path)]}

