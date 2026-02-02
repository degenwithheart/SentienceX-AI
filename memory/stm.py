from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from typing import Deque, Iterable, List, Optional


@dataclass(frozen=True)
class Turn:
    turn_id: int
    ts: float
    role: str  # "user" | "assistant"
    text: str
    meta: dict


class ShortTermMemory:
    def __init__(self, max_turns: int):
        self._max_turns = max_turns
        self._buf: Deque[Turn] = deque(maxlen=max_turns)

    def add(self, turn: Turn) -> None:
        self._buf.append(turn)

    def last(self, n: int) -> List[Turn]:
        if n <= 0:
            return []
        return list(self._buf)[-n:]

    def last_user(self) -> Optional[Turn]:
        for t in reversed(self._buf):
            if t.role == "user":
                return t
        return None

    def iter(self) -> Iterable[Turn]:
        return list(self._buf)

    def clear(self) -> None:
        self._buf.clear()

