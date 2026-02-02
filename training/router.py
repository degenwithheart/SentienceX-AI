from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Optional

from locale_pack.loader import LocalePack
from training.schedule import TrainingConfig, TrainingRunner
from training.state import TrainingState


def default_state_path(data_dir: Path) -> Path:
    return data_dir / "training_state.json"


class TrainingOrchestrator:
    def __init__(self, locale: LocalePack, cfg: TrainingConfig):
        self._locale = locale
        self._cfg = cfg
        self._state_path = default_state_path(cfg.data_dir)
        self._state = TrainingState.load(self._state_path)
        self._runner = TrainingRunner(locale=locale, cfg=cfg, state=self._state)

    @property
    def state(self) -> TrainingState:
        return self._state

    def status(self) -> dict:
        return {
            "train_dir": str(self._cfg.train_dir),
            "data_dir": str(self._cfg.data_dir),
            "updated_at": self._state.updated_at,
            "last_runs": self._state.last_runs,
            "tracked_files": len(self._state.files),
        }

    def run(self, modules: Optional[List[str]] = None, force_full: bool = False) -> Dict[str, dict]:
        res = self._runner.run(modules=modules, force_full=force_full)
        self._state.save(self._state_path)
        return res
