from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Iterator, Optional


@dataclass(frozen=True)
class WeakSample:
    label: str
    text: str
    weight: float


def _safe_label(label: str) -> str:
    return "".join(ch for ch in label.lower().strip() if ch.isalnum() or ch in {"_", "-"}).strip("-_")


class WeakLabelWriter:
    def __init__(self, base_dir: Path):
        self._base = base_dir

    def append(self, task: str, sample: WeakSample) -> None:
        task_dir = self._base / task
        task_dir.mkdir(parents=True, exist_ok=True)
        lab = _safe_label(sample.label) or "unknown"
        p = task_dir / f"{lab}.txt"
        # Keep file format compatible with supervised dataset (1 sample per line).
        with p.open("a", encoding="utf-8") as f:
            f.write(sample.text.replace("\n", " ").strip() + "\n")

