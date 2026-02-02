from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Optional, Tuple


@dataclass
class FileOffset:
    mtime: float
    size: int
    offset: int


@dataclass
class TrainingState:
    updated_at: float = 0.0
    files: Dict[str, FileOffset] = field(default_factory=dict)
    last_runs: Dict[str, float] = field(default_factory=dict)
    carry: Dict[str, object] = field(default_factory=dict)

    @staticmethod
    def load(path: Path) -> "TrainingState":
        if not path.exists():
            return TrainingState()
        obj = json.loads(path.read_text(encoding="utf-8"))
        ts = TrainingState()
        ts.updated_at = float(obj.get("updated_at", 0.0))
        ts.last_runs = {k: float(v) for k, v in obj.get("last_runs", {}).items()}
        ts.carry = dict(obj.get("carry", {}))
        files: Dict[str, FileOffset] = {}
        for fp, fo in obj.get("files", {}).items():
            files[str(fp)] = FileOffset(mtime=float(fo["mtime"]), size=int(fo["size"]), offset=int(fo["offset"]))
        ts.files = files
        return ts

    def save(self, path: Path) -> None:
        self.updated_at = time.time()
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(
                {
                    "updated_at": self.updated_at,
                    "last_runs": self.last_runs,
                    "files": {k: {"mtime": v.mtime, "size": v.size, "offset": v.offset} for k, v in self.files.items()},
                    "carry": self.carry,
                },
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )

    def key_for(self, path: Path) -> str:
        return str(path.resolve())

    def get_offset(self, path: Path) -> Optional[FileOffset]:
        return self.files.get(self.key_for(path))

    def set_offset(self, path: Path, offset: int) -> None:
        st = path.stat()
        self.files[self.key_for(path)] = FileOffset(mtime=st.st_mtime, size=st.st_size, offset=int(offset))

    def should_reset(self, path: Path) -> bool:
        fo = self.get_offset(path)
        if fo is None:
            return True
        st = path.stat()
        if st.st_size < fo.offset:
            return True
        if st.st_mtime != fo.mtime and st.st_size < fo.size:
            return True
        return False

    def mark_run(self, name: str) -> None:
        self.last_runs[name] = time.time()
