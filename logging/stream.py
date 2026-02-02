from __future__ import annotations

import asyncio
import json
import time
from dataclasses import dataclass
from typing import Any, AsyncIterator, Dict, Optional


@dataclass(frozen=True)
class Event:
    ts: float
    name: str
    data: Dict[str, Any]

    def to_sse(self) -> str:
        payload = json.dumps({"ts": self.ts, "name": self.name, "data": self.data}, ensure_ascii=False)
        return f"event: {self.name}\ndata: {payload}\n\n"


class EventBus:
    def __init__(self):
        self._q: "asyncio.Queue[Event]" = asyncio.Queue(maxsize=2000)
        self.enabled: bool = True

    def publish(self, name: str, data: Dict[str, Any]) -> None:
        if not self.enabled:
            return
        ev = Event(ts=time.time(), name=name, data=data)
        try:
            self._q.put_nowait(ev)
        except asyncio.QueueFull:
            # Drop oldest by draining a bit to keep the stream live.
            try:
                _ = self._q.get_nowait()
            except asyncio.QueueEmpty:
                pass
            try:
                self._q.put_nowait(ev)
            except asyncio.QueueFull:
                pass

    async def subscribe(self) -> AsyncIterator[Event]:
        while True:
            ev = await self._q.get()
            yield ev
