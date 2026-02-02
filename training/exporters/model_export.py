from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Dict


def write_model(path: Path, model_obj: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        backup = path.with_suffix(path.suffix + f".bak.{int(time.time())}")
        backup.write_text(path.read_text(encoding="utf-8"), encoding="utf-8")
    path.write_text(json.dumps(model_obj, ensure_ascii=False), encoding="utf-8")


def write_models(models_dir: Path, models: Dict[str, dict]) -> None:
    for name, obj in models.items():
        write_model(models_dir / name, obj)

