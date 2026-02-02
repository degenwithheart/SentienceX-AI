from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional


def _root() -> Path:
    return Path(__file__).resolve().parents[1]


_CACHE: Dict[str, tuple[float, dict]] = {}


def load_json_cached(rel_path: str) -> Optional[dict]:
    path = _root() / rel_path
    if not path.exists():
        return None
    mtime = path.stat().st_mtime
    cached = _CACHE.get(str(path))
    if cached and cached[0] == mtime:
        return cached[1]
    try:
        obj = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None
    _CACHE[str(path)] = (mtime, obj)
    return obj


def hidden_priors() -> Optional[dict]:
    return load_json_cached("cognition/hidden_emotion_priors.json")


def masking_patterns() -> Optional[dict]:
    return load_json_cached("cognition/masking_patterns.json")


def social_withdrawal() -> Optional[dict]:
    return load_json_cached("cognition/social_withdrawal.json")


def proactive_priors() -> Optional[dict]:
    return load_json_cached("cognition/proactive_priors.json")


def policy_priors() -> Optional[dict]:
    return load_json_cached("cognition/policy_priors.json")

