from __future__ import annotations

import json
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from locale_pack.loader import LocalePack


def _root() -> Path:
    return Path(__file__).resolve().parents[2]


def _load_turns(path: Path) -> List[dict]:
    if not path.exists():
        return []
    out: List[dict] = []
    for ln in path.read_text(encoding="utf-8").splitlines():
        if not ln.strip():
            continue
        out.append(json.loads(ln))
    return out


def _bucket(x: float, cuts: List[float]) -> int:
    for i, c in enumerate(cuts):
        if x < c:
            return i
    return len(cuts)


def update_policy_priors(locale: LocalePack, data_dir: Path, conversations: Dict[str, object]) -> Dict[str, object]:
    """
    Learns route priors from real runtime logs (data/turns.jsonl) by looking at:
    user inference state -> assistant tone -> engagement (time to next user).
    Exports small bias tables used by the dialogue policy.
    """
    turns_path = data_dir / "turns.jsonl"
    rows = _load_turns(turns_path)
    if len(rows) < 6:
        out = {"version": 1, "source": "data/turns.jsonl", "priors": {}, "counts": {}}
        (_root() / "cognition" / "policy_priors.json").write_text(json.dumps(out, ensure_ascii=False), encoding="utf-8")
        return {"exported": ["cognition/policy_priors.json"], "pairs": 0}

    # Build user->assistant->user triples.
    triples: List[Tuple[dict, dict, Optional[dict]]] = []
    for i in range(len(rows) - 1):
        if rows[i].get("role") != "user":
            continue
        if rows[i + 1].get("role") != "assistant":
            continue
        nxt = None
        for j in range(i + 2, min(len(rows), i + 8)):
            if rows[j].get("role") == "user":
                nxt = rows[j]
                break
        triples.append((rows[i], rows[i + 1], nxt))

    # Aggregate: key = (intent, sentiment, hidden_bin) -> tone -> [success, total]
    agg: Dict[str, Dict[str, List[float]]] = {}
    total_pairs = 0

    for u, a, nxt in triples:
        uinf = (u.get("meta", {}) or {}).get("inference", {})
        intent = (uinf.get("intent", {}) or {}).get("label", "unknown")
        sentiment = (uinf.get("sentiment", {}) or {}).get("label", "neu")
        hidden = float((uinf.get("hidden", {}) or {}).get("distress_score", 0.0))
        hb = _bucket(hidden, [0.35, 0.62, 0.75])

        tone = (a.get("meta", {}) or {}).get("tone", "normal")
        ats = float(a.get("ts", 0.0))
        success = 0.0
        if nxt is not None:
            dts = float(nxt.get("ts", 0.0)) - ats
            if 0 < dts <= 7 * 60:
                success = 1.0
            elif dts > 20 * 60:
                success = 0.0
            else:
                success = 0.4

        key = f"intent={intent}|sent={sentiment}|hb={hb}"
        agg.setdefault(key, {}).setdefault(tone, [0.0, 0.0])
        agg[key][tone][0] += success
        agg[key][tone][1] += 1.0
        total_pairs += 1

    # Convert to bias values: centered success rate vs global.
    global_s = sum(v[0] for m in agg.values() for v in m.values())
    global_n = sum(v[1] for m in agg.values() for v in m.values()) or 1.0
    global_rate = global_s / global_n

    priors: Dict[str, Dict[str, float]] = {}
    counts: Dict[str, Dict[str, int]] = {}
    for key, tones in agg.items():
        priors[key] = {}
        counts[key] = {}
        for tone, (s, n) in tones.items():
            rate = s / (n or 1.0)
            # Bias scale small to avoid destabilizing the hand-built policy.
            priors[key][tone] = float((rate - global_rate) * 0.8)
            counts[key][tone] = int(n)

    out = {"version": 1, "source": "data/turns.jsonl", "global_rate": global_rate, "priors": priors, "counts": counts}
    cog_dir = _root() / "cognition"
    cog_dir.mkdir(parents=True, exist_ok=True)
    (cog_dir / "policy_priors.json").write_text(json.dumps(out, ensure_ascii=False), encoding="utf-8")
    return {"exported": ["cognition/policy_priors.json"], "pairs": total_pairs, "global_rate": global_rate}

