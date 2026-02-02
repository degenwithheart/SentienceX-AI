from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, Iterator, List, Optional, Tuple

from locale_pack.loader import LocalePack
from nlp.normalizer import Normalizer


def _walk(folder: Path) -> Iterator[Path]:
    if not folder.exists():
        return iter(())
    for root, _, fns in os.walk(folder):
        for fn in sorted(fns):
            if fn.startswith("."):
                continue
            p = Path(root) / fn
            if p.suffix.lower() not in {".txt", ".jsonl"}:
                continue
            yield p


_ROLE_RE = re.compile(r"^(user|assistant)\s*:\s*", re.IGNORECASE)


@dataclass(frozen=True)
class ConvTurn:
    role: str
    text: str
    ts: Optional[float] = None


@dataclass(frozen=True)
class Conversation:
    source: str
    turns: List[ConvTurn]


def _parse_txt(normalizer: Normalizer, text: str) -> List[ConvTurn]:
    turns: List[ConvTurn] = []
    cur_role: Optional[str] = None
    buf: List[str] = []

    def flush() -> None:
        nonlocal buf, cur_role
        if cur_role and buf:
            turns.append(ConvTurn(role=cur_role, text=normalizer.apply("\n".join(buf))))
        buf = []

    for raw in text.splitlines():
        m = _ROLE_RE.match(raw.strip())
        if m:
            flush()
            cur_role = m.group(1).lower()
            rest = raw[m.end() :].strip()
            if rest:
                buf.append(rest)
        else:
            if raw.strip() == "" and buf:
                # paragraph break
                buf.append("")
            else:
                if cur_role is None:
                    continue
                buf.append(raw.rstrip())
    flush()
    return [t for t in turns if t.text.strip()]


def _parse_jsonl(normalizer: Normalizer, text: str) -> List[ConvTurn]:
    turns: List[ConvTurn] = []
    for ln in text.splitlines():
        s = ln.strip()
        if not s:
            continue
        obj = json.loads(s)
        role = str(obj.get("role", "")).lower().strip()
        if role not in {"user", "assistant"}:
            continue
        msg = str(obj.get("text", "")).strip()
        if not msg:
            continue
        ts = obj.get("ts", None)
        ts_f = float(ts) if ts is not None else None
        turns.append(ConvTurn(role=role, text=normalizer.apply(msg), ts=ts_f))
    return turns


def ingest_raw_conversations(locale: LocalePack, train_dir: Path) -> Dict[str, object]:
    folder = train_dir / "raw_conversations"
    normalizer = Normalizer.from_rule_lines(locale.normalize_rules)

    convs: List[Conversation] = []
    for p in _walk(folder):
        raw = p.read_text(encoding="utf-8", errors="ignore").strip()
        if not raw:
            continue
        if p.suffix.lower() == ".jsonl":
            turns = _parse_jsonl(normalizer, raw)
        else:
            turns = _parse_txt(normalizer, raw)
        if len(turns) >= 2:
            convs.append(Conversation(source=str(p), turns=turns))

    # `convs` is kept for internal mining; API surfaces should not serialize it.
    return {"conversations": len(convs), "sources": [c.source for c in convs[:50]], "convs": convs}
