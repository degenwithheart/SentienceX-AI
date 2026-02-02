from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List


@dataclass(frozen=True)
class FlowStats:
    transitions: Dict[str, Dict[str, int]]

    def add(self, a: str, b: str) -> None:
        self.transitions.setdefault(a, {}).setdefault(b, 0)
        self.transitions[a][b] += 1

    def probs(self) -> Dict[str, Dict[str, float]]:
        out: Dict[str, Dict[str, float]] = {}
        for a, row in self.transitions.items():
            total = sum(row.values()) or 1
            out[a] = {b: v / total for b, v in row.items()}
        return out

