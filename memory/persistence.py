from __future__ import annotations

import json
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from cognition.contradiction import Claim
from locale_pack.loader import LocalePack
from logging.stream import EventBus
from memory.episodic import EpisodicMemory
from memory.index import InvertedIndex
from memory.semantic import SemanticMemory
from memory.stm import ShortTermMemory, Turn
from nlp.segmenter import Segmenter


@dataclass(frozen=True)
class RetrievedMemory:
    turns: List[Turn]
    episodes: List[dict]
    facts: List[Claim]


class MemoryStore:
    def __init__(self, data_dir: Path, locale: LocalePack, stm_turns: int, events: EventBus):
        self._data_dir = data_dir
        self._locale = locale
        self._events = events

        self._turns_path = data_dir / "turns.jsonl"
        self._feedback_path = data_dir / "feedback.jsonl"
        self._semantic_path = data_dir / "semantic.json"
        self._index_path = data_dir / "index.json"
        self._episodes_path = data_dir / "episodes.jsonl"

        self.stm = ShortTermMemory(max_turns=stm_turns)
        self.semantic = SemanticMemory.load(self._semantic_path)
        self.episodes = EpisodicMemory(self._episodes_path, locale=locale)
        self.index = InvertedIndex.open(self._index_path)
        self._seg = Segmenter(locale.alphabet)

        self._next_turn_id = 1
        self._load_turns_into_stm(max_turns=stm_turns)

        # Episode tracking
        self._episode_open_since: Optional[float] = None
        self._episode_turn_texts: List[str] = []
        self._episode_distress: List[float] = []
        self._last_turn_ts: float = self.semantic.last_turn_ts or 0.0

    @staticmethod
    def open(data_dir: Path, locale: LocalePack, stm_turns: int, events: EventBus) -> "MemoryStore":
        data_dir.mkdir(parents=True, exist_ok=True)
        return MemoryStore(data_dir=data_dir, locale=locale, stm_turns=stm_turns, events=events)

    def _load_turns_into_stm(self, max_turns: int) -> None:
        if not self._turns_path.exists():
            return
        lines = self._turns_path.read_text(encoding="utf-8").splitlines()
        tail = lines[-max_turns:]
        for ln in tail:
            obj = json.loads(ln)
            t = Turn(
                turn_id=int(obj["turn_id"]),
                ts=float(obj["ts"]),
                role=str(obj["role"]),
                text=str(obj["text"]),
                meta=dict(obj.get("meta", {})),
            )
            self.stm.add(t)
            self._next_turn_id = max(self._next_turn_id, t.turn_id + 1)

    def add_turn(self, role: str, text: str, meta: Optional[dict] = None) -> Turn:
        now = time.time()
        t = Turn(turn_id=self._next_turn_id, ts=now, role=role, text=text, meta=meta or {})
        self._next_turn_id += 1

        self._turns_path.parent.mkdir(parents=True, exist_ok=True)
        with self._turns_path.open("a", encoding="utf-8") as f:
            f.write(json.dumps({"turn_id": t.turn_id, "ts": t.ts, "role": t.role, "text": t.text, "meta": t.meta}, ensure_ascii=False) + "\n")

        self.stm.add(t)
        self.index.add_document(self._seg, t.turn_id, t.text)

        self._events.publish("memory.turn", {"turn_id": t.turn_id, "role": role})
        return t

    def update_semantic(self, claims: List[Claim], topic_salience: Dict[str, float], distress_score: float) -> None:
        now = time.time()
        self.semantic.update_facts(claims, now=now)
        self.semantic.update_topics(topic_salience, now=now)
        self.semantic.update_emotions(distress_score)
        self.semantic.last_turn_ts = now
        self.semantic.save(self._semantic_path)
        self._events.publish("memory.semantic", {"facts": len(self.semantic.facts), "topics": len(self.semantic.topics)})

    def add_feedback(self, payload: dict) -> None:
        payload = dict(payload)
        payload["ts"] = time.time()
        self._feedback_path.parent.mkdir(parents=True, exist_ok=True)
        with self._feedback_path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(payload, ensure_ascii=False) + "\n")
        self._events.publish("memory.feedback", {"kind": payload.get("kind")})

    def retrieve(self, query: str, limit_turns: int = 10, scan_tail_lines: int = 8000) -> RetrievedMemory:
        hits = self.index.search(self._seg, query, limit=limit_turns)
        if not hits:
            return RetrievedMemory(turns=[], episodes=[], facts=self.semantic.facts)
        ids = {doc_id for doc_id, _ in hits}

        turns: List[Turn] = []
        if self._turns_path.exists():
            # Scan from the end; typical usage wants recent related context.
            tail_n = max(500, int(scan_tail_lines))
            for ln in reversed(self._turns_path.read_text(encoding="utf-8").splitlines()[-tail_n:]):
                if len(turns) >= limit_turns:
                    break
                obj = json.loads(ln)
                tid = int(obj["turn_id"])
                if tid not in ids:
                    continue
                turns.append(
                    Turn(
                        turn_id=tid,
                        ts=float(obj["ts"]),
                        role=str(obj["role"]),
                        text=str(obj["text"]),
                        meta=dict(obj.get("meta", {})),
                    )
                )

        turns.sort(key=lambda t: t.turn_id)
        episodes = [e.__dict__ for e in self.episodes.recent(6)]
        return RetrievedMemory(turns=turns, episodes=episodes, facts=self.semantic.facts)

    def maybe_close_episode(self) -> None:
        if self._episode_open_since is None:
            return
        if not self._episode_turn_texts:
            self._episode_open_since = None
            return
        now = time.time()
        self.episodes.add(
            started_at=self._episode_open_since,
            ended_at=now,
            turns=self._episode_turn_texts,
            distress_scores=self._episode_distress,
        )
        self._episode_open_since = None
        self._episode_turn_texts = []
        self._episode_distress = []

    def track_episode_turn(self, text: str, distress_score: float) -> None:
        now = time.time()
        if self._episode_open_since is None:
            self._episode_open_since = now
        # New episode after long gap.
        if self._last_turn_ts and (now - self._last_turn_ts) > 2 * 3600:
            self.maybe_close_episode()
            self._episode_open_since = now
        self._episode_turn_texts.append(text)
        self._episode_distress.append(float(distress_score))
        self._last_turn_ts = now

    def compact(self) -> None:
        # Flush index and semantic; JSONL is append-only (intentionally).
        self.index.flush()
        self.semantic.save(self._semantic_path)
        self._events.publish("memory.compact", {"doc_count": self.index.doc_count})

    def close(self) -> None:
        self.maybe_close_episode()
        self.compact()
