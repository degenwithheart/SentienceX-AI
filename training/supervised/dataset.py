from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterator, List, Tuple

from locale_pack.loader import LocalePack
from training.loader import StreamLoader
from training.state import TrainingState


@dataclass(frozen=True)
class LabeledSample:
    label: str
    text: str
    source: str


def _label_from_filename(path: Path) -> str:
    return path.stem.strip().lower()


def iter_label_files(folder: Path) -> List[Path]:
    if not folder.exists():
        return []
    files: List[Path] = []
    for root, _, fns in os.walk(folder):
        for fn in sorted(fns):
            if fn.startswith("."):
                continue
            p = Path(root) / fn
            if p.suffix.lower() != ".txt":
                continue
            files.append(p)
    return files


def stream_samples(locale: LocalePack, folder: Path, state: TrainingState, force_full: bool = False) -> Iterator[LabeledSample]:
    loader = StreamLoader(locale)
    for fp in iter_label_files(folder):
        label = _label_from_filename(fp)
        if not label:
            continue
        if force_full:
            # Reset offset to start.
            state.files.pop(state.key_for(fp), None)
        for ll in loader.iter_lines_incremental(fp, state):
            yield LabeledSample(label=label, text=ll.text, source=str(fp))


def labels_in_folder(folder: Path) -> List[str]:
    labs: List[str] = []
    for fp in iter_label_files(folder):
        lab = _label_from_filename(fp)
        if lab:
            labs.append(lab)
    return sorted(set(labs))

