from __future__ import annotations

from dataclasses import dataclass
from typing import Dict


@dataclass(frozen=True)
class MaskingStats:
    masking_total: int
    masking_and_distress: int

    def p_hidden_given_masking(self) -> float:
        if self.masking_total <= 0:
            return 0.0
        return self.masking_and_distress / self.masking_total

