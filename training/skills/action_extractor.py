from __future__ import annotations

import re
from dataclasses import dataclass
from typing import List


_LEAD_VERB_RE = re.compile(r"^(try|do|make|write|list|call|text|ask|set|schedule|consider|avoid|keep|start|stop|pick)\b", re.IGNORECASE)


def extract_actions(text: str) -> List[str]:
    actions: List[str] = []
    for raw in re.split(r"[\n\r]+", text):
        s = raw.strip()
        if not s or s.startswith("#"):
            continue
        s = re.sub(r"^[\-\*\d\.\)\s]+", "", s).strip()
        if not s:
            continue
        # Use first sentence if paragraph.
        s = re.split(r"(?<=[.!?])\s+", s)[0].strip()
        if not s:
            continue
        if _LEAD_VERB_RE.search(s):
            actions.append(s)
        # Also capture "You can ..." suggestions as actions.
        elif s.lower().startswith("you can "):
            actions.append(s)
        elif s.lower().startswith("consider "):
            actions.append(s)
    # Deduplicate, keep order.
    seen = set()
    out: List[str] = []
    for a in actions:
        k = a.lower()
        if k in seen:
            continue
        seen.add(k)
        out.append(a)
    return out

