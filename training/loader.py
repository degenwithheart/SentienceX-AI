from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Iterator, Optional, Tuple

from locale_pack.loader import LocalePack
from nlp.normalizer import Normalizer
from nlp.sentence_splitter import SentenceSplitter
from training.state import TrainingState


@dataclass(frozen=True)
class LoadedLine:
    path: Path
    offset_after: int
    text: str


class StreamLoader:
    def __init__(self, locale: LocalePack):
        self._locale = locale
        self._normalizer = Normalizer.from_rule_lines(locale.normalize_rules)
        self._splitter = SentenceSplitter(locale.abbreviations)

    def iter_lines_incremental(self, path: Path, state: TrainingState) -> Iterator[LoadedLine]:
        if not path.exists():
            return iter(())

        reset = state.should_reset(path)
        start = 0 if reset else (state.get_offset(path).offset if state.get_offset(path) else 0)
        with path.open("r", encoding="utf-8", errors="ignore") as f:
            f.seek(start)
            while True:
                pos = f.tell()
                line = f.readline()
                if not line:
                    break
                raw = line.strip()
                if not raw or raw.startswith("#"):
                    state.set_offset(path, f.tell())
                    continue
                text = self._normalizer.apply(raw)
                yield LoadedLine(path=path, offset_after=f.tell(), text=text)
                state.set_offset(path, f.tell())

    def iter_docs(self, folder: Path) -> Iterator[Tuple[Path, str]]:
        if not folder.exists():
            return iter(())

        def walk() -> Iterable[Path]:
            for root, _, files in os.walk(folder):
                for fn in sorted(files):
                    if fn.startswith("."):
                        continue
                    p = Path(root) / fn
                    if p.is_file():
                        yield p

        for p in walk():
            txt = p.read_text(encoding="utf-8", errors="ignore").strip()
            if not txt:
                continue
            yield p, self._normalizer.apply(txt)

    def sentences(self, text: str) -> list[str]:
        return [s.text for s in self._splitter.split(text)]

