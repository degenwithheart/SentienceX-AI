from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class Budget:
    cpu_percent_max: float = 50.0
    mem_percent_max: float = 50.0


@dataclass(frozen=True)
class DegradeHints:
    level: str  # "none" | "light" | "hard"
    retrieval_limit_turns: int
    scan_tail_lines: int
    allow_proactive: bool
    allow_actions: bool


class ResourceGovernor:
    def __init__(self, resources, *, user_budget: Optional[Budget] = None):
        self._resources = resources
        self._user_budget = user_budget or Budget()

    def snapshot(self):
        return self._resources.snapshot()

    def over_budget_user(self) -> bool:
        snap = self.snapshot()
        cpu = float(getattr(snap, "cpu_percent", 0.0) or 0.0)
        mem = float(getattr(snap, "mem_percent", 0.0) or 0.0)
        return cpu > self._user_budget.cpu_percent_max or mem > self._user_budget.mem_percent_max

    def hints_for_user(self) -> DegradeHints:
        snap = self.snapshot()
        cpu = float(getattr(snap, "cpu_percent", 0.0) or 0.0)
        mem = float(getattr(snap, "mem_percent", 0.0) or 0.0)

        if cpu <= self._user_budget.cpu_percent_max and mem <= self._user_budget.mem_percent_max:
            return DegradeHints(level="none", retrieval_limit_turns=10, scan_tail_lines=8000, allow_proactive=True, allow_actions=True)

        # Light degrade (just over budget)
        if cpu < 70.0 and mem < 70.0:
            return DegradeHints(level="light", retrieval_limit_turns=4, scan_tail_lines=2000, allow_proactive=False, allow_actions=False)

        # Hard degrade (system hot): minimal work
        return DegradeHints(level="hard", retrieval_limit_turns=0, scan_tail_lines=0, allow_proactive=False, allow_actions=False)

