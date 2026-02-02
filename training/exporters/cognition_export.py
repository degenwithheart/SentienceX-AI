from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Dict


def write_artifact(path: Path, obj: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        backup = path.with_suffix(path.suffix + f".bak.{int(time.time())}")
        backup.write_text(path.read_text(encoding="utf-8"), encoding="utf-8")
    path.write_text(json.dumps(obj, ensure_ascii=False), encoding="utf-8")


def write_artifacts(base_dir: Path, artifacts: Dict[str, dict]) -> None:
    for rel, obj in artifacts.items():
        write_artifact(base_dir / rel, obj)

