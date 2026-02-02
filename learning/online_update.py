from __future__ import annotations

import json
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from learning.feedback import FeedbackSignal, implicit_from_engagement, parse_explicit
from learning.template_ranker import TemplateRanker, load_ranker, save_ranker
from learning.tone_preference import TonePreference, load_tone, save_tone
from logging.stream import EventBus
from memory.persistence import MemoryStore


@dataclass
class LastResponse:
    ts: float
    template_id: str
    tone: str


class OnlineUpdater:
    def __init__(self, store: MemoryStore, events: EventBus):
        self._store = store
        self._events = events
        self._path = store._data_dir / "learning.json"  # persisted state

        self.template_ranker: TemplateRanker
        self.tone_pref: TonePreference
        self.last_response: Optional[LastResponse] = None

        self._load()

    def _load(self) -> None:
        if self._path.exists():
            obj = json.loads(self._path.read_text(encoding="utf-8"))
            self.template_ranker = TemplateRanker.from_json(obj.get("template_ranker", {}))
            self.tone_pref = TonePreference.from_json(obj.get("tone_pref", {}))
        else:
            self.template_ranker = TemplateRanker()
            self.tone_pref = TonePreference()

    def save(self) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._path.write_text(
            json.dumps(
                {"template_ranker": self.template_ranker.to_json(), "tone_pref": self.tone_pref.to_json()},
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )

    def note_response(self, template_id: str, tone: str) -> None:
        self.last_response = LastResponse(ts=time.time(), template_id=template_id, tone=tone)
        self._events.publish("learning.note_response", {"template_id": template_id, "tone": tone})

    def on_user_message(self) -> None:
        if not self.last_response:
            return
        dt = time.time() - self.last_response.ts
        sig = implicit_from_engagement(dt)
        self.apply_signal(sig, template_id=self.last_response.template_id, tone=self.last_response.tone)

    def apply_explicit_feedback(self, payload: dict) -> None:
        sig = parse_explicit(payload)
        self.apply_signal(sig, template_id=sig.template_id, tone=sig.tone)

    def apply_signal(self, sig: FeedbackSignal, template_id: Optional[str], tone: Optional[str]) -> None:
        if template_id:
            self.template_ranker.update(template_id, success=sig.success, weight=sig.weight)
        if tone:
            self.tone_pref.update(tone, reward=(1.0 if sig.success else -1.0) * sig.weight)
        self.save()
        self._events.publish(
            "learning.update",
            {"kind": sig.kind, "success": sig.success, "weight": sig.weight, "template_id": template_id, "tone": tone},
        )

