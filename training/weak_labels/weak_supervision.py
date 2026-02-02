from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from locale_pack.loader import LocalePack
from training.state import TrainingState
from training.weak_labels.self_label_buffer import WeakLabelWriter, WeakSample


def _iter_jsonl_incremental(path: Path, state: TrainingState, carry_key: str, force_full: bool = False) -> List[dict]:
    if not path.exists():
        return []
    if force_full:
        state.files.pop(state.key_for(path), None)
        state.carry.pop(carry_key, None)

    reset = state.should_reset(path)
    start = 0 if reset else (state.get_offset(path).offset if state.get_offset(path) else 0)
    prev = state.carry.get(carry_key, None)
    prev_list: List[dict] = []
    if isinstance(prev, list):
        prev_list = [x for x in prev if isinstance(x, dict)][-2:]

    out: List[dict] = []
    with path.open("r", encoding="utf-8", errors="ignore") as f:
        f.seek(start)
        for ln in f:
            s = ln.strip()
            if not s:
                continue
            try:
                out.append(json.loads(s))
            except Exception:
                continue
        state.set_offset(path, f.tell())

    # Preserve the last two turns across incremental runs.
    tail = (prev_list + out)[-2:]
    state.carry[carry_key] = tail
    return prev_list + out


def build_weak_label_sets(locale: LocalePack, data_dir: Path, train_dir: Path, state: TrainingState, force_full: bool = False) -> Dict[str, object]:
    """
    Converts high-confidence runtime predictions into weak supervised samples.

    Source:
      data/turns.jsonl (user turns include stored inference in meta)

    Acceptance heuristic:
      If the assistant reply immediately after the user message is followed by another user message within 7 minutes.

    Output:
      data/weak_labels/{intent|sentiment|sarcasm|threat}/<label>.txt
    """
    turns = _iter_jsonl_incremental(data_dir / "turns.jsonl", state=state, carry_key="weak.turns_tail", force_full=force_full)
    if len(turns) < 6:
        return {"generated": False, "reason": "not enough turns"}

    writer = WeakLabelWriter(base_dir=data_dir / "weak_labels")
    written = {"intent": 0, "sentiment": 0, "sarcasm": 0, "threat": 0}

    for i in range(len(turns) - 2):
        u = turns[i]
        a = turns[i + 1]
        nxt = turns[i + 2]
        if u.get("role") != "user" or a.get("role") != "assistant" or nxt.get("role") != "user":
            continue
        dt = float(nxt.get("ts", 0.0)) - float(a.get("ts", 0.0))
        if not (0 < dt <= 7 * 60):
            continue

        meta = u.get("meta", {}) or {}
        inf = meta.get("inference", {}) or {}

        text = str(u.get("text", "")).strip()
        if not text:
            continue

        # Intent
        il = (inf.get("intent", {}) or {}).get("label", None)
        ic = float((inf.get("intent", {}) or {}).get("confidence", 0.0))
        if il and ic >= 0.75:
            writer.append("intent", WeakSample(label=str(il), text=text, weight=0.45))
            written["intent"] += 1

        # Sentiment
        sl = (inf.get("sentiment", {}) or {}).get("label", None)
        sc = float((inf.get("sentiment", {}) or {}).get("confidence", 0.0))
        if sl and sc >= 0.75:
            writer.append("sentiment", WeakSample(label=str(sl), text=text, weight=0.45))
            written["sentiment"] += 1

        # Sarcasm
        sar = (inf.get("sarcasm", {}) or {}).get("is_sarcastic", None)
        sarc = float((inf.get("sarcasm", {}) or {}).get("confidence", 0.0))
        if sar is not None and sarc >= 0.80:
            lab = "sarcastic" if bool(sar) else "not_sarcastic"
            writer.append("sarcasm", WeakSample(label=lab, text=text, weight=0.40))
            written["sarcasm"] += 1

        # Threat
        tl = (inf.get("threat", {}) or {}).get("label", None)
        tc = float((inf.get("threat", {}) or {}).get("confidence", 0.0))
        if tl and tc >= 0.85:
            writer.append("threat", WeakSample(label=str(tl), text=text, weight=0.35))
            written["threat"] += 1

    return {"generated": True, "written": written, "output_dir": str(data_dir / "weak_labels")}
