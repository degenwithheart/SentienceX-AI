from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class DialogueState:
    turn_count: int = 0
    last_user_ts: float = 0.0
    last_ai_ts: float = 0.0
    last_tone: str = "normal"
    last_template_id: str = ""
    last_advice_turn: int = -999
    last_proactive_turn: int = -999
    last_proactive_ts: float = 0.0

    def bump_user(self) -> None:
        self.turn_count += 1
        self.last_user_ts = time.time()

    def bump_ai(self, tone: str, template_id: str) -> None:
        self.turn_count += 1
        self.last_ai_ts = time.time()
        self.last_tone = tone
        self.last_template_id = template_id

