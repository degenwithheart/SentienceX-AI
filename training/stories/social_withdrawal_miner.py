from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class WithdrawalStats:
    after_total: int
    short_after: int
    short_len_chars: int = 28

    def p_short_after_distress(self) -> float:
        if self.after_total <= 0:
            return 0.0
        return self.short_after / self.after_total

