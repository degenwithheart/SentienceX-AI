from __future__ import annotations

import time
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Optional, Tuple

from app.config import Settings
from cognition.learned import policy_priors
from cognition.inference_state import InferenceState
from dialogue.brevity import choose_brevity
from dialogue.composer import Composed, compose, reflect_phrase
from dialogue.proactive import choose_proactive
from dialogue.state import DialogueState
from learning.online_update import OnlineUpdater
from locale_pack.loader import LocalePack
from logging.stream import EventBus
from memory.persistence import MemoryStore, RetrievedMemory
from monitoring.governor import ResourceGovernor
from nlp.features import make_context
from knowledge.store import KnowledgeStore
from style.extractor import extract_style
from style.profile import load_style, save_style
from style.shaper import shape_reply


@dataclass(frozen=True)
class ChatOutput:
    reply: str
    tone: str
    template_id: str
    brevity: str
    meta: dict


class DialoguePolicy:
    def __init__(self, settings: Settings, locale: LocalePack, memory: MemoryStore, metrics, updater: OnlineUpdater, events: EventBus):
        self._settings = settings
        self._locale = locale
        self._memory = memory
        self._metrics = metrics
        self._updater = updater
        self._events = events
        self._state = DialogueState()
        self._style_path = memory._data_dir / "style.json"  # persisted state
        self._style = load_style(self._style_path)
        self._knowledge = KnowledgeStore.load()
        self._policy_priors = policy_priors() or {}
        self._knowledge_sig = self._knowledge_signature()
        self._policy_priors_mtime = self._policy_priors_signature()
        self._governor: ResourceGovernor | None = None

    @property
    def state(self) -> DialogueState:
        return self._state

    def _root(self) -> Path:
        return Path(__file__).resolve().parents[1]

    def _knowledge_signature(self) -> tuple[float, float]:
        root = self._root()
        topics_path = root / "knowledge" / "topics.json"
        actions_dir = root / "knowledge" / "actions"
        t_m = topics_path.stat().st_mtime if topics_path.exists() else 0.0
        a_m = 0.0
        if actions_dir.exists():
            for p in actions_dir.glob("*.json"):
                try:
                    a_m = max(a_m, p.stat().st_mtime)
                except Exception:
                    continue
        return (t_m, a_m)

    def _policy_priors_signature(self) -> float:
        p = self._root() / "cognition" / "policy_priors.json"
        return p.stat().st_mtime if p.exists() else 0.0

    def refresh_artifacts(self) -> None:
        """
        Reload small learned artifacts produced by training without restarting:
        - knowledge/topics.json and knowledge/actions/*.json
        - cognition/policy_priors.json
        """
        # Knowledge
        sig = self._knowledge_signature()
        if sig != self._knowledge_sig:
            self._knowledge = KnowledgeStore.load()
            self._knowledge_sig = sig
            try:
                self._events.publish("artifacts.reload", {"kind": "knowledge"})
            except Exception:
                pass

    def set_governor(self, governor: ResourceGovernor) -> None:
        self._governor = governor

        # Policy priors
        pm = self._policy_priors_signature()
        if pm != self._policy_priors_mtime:
            self._policy_priors = policy_priors() or {}
            self._policy_priors_mtime = pm
            try:
                self._events.publish("artifacts.reload", {"kind": "policy_priors"})
            except Exception:
                pass

    def _topic_salience(self, normalized_l: str) -> Dict[str, float]:
        topics: Dict[str, float] = {}
        for phrase in self._locale.lexicons.distress_topics:
            if phrase in normalized_l:
                topics[phrase] = 1.0
        # Learned topics
        for topic, tp in self._knowledge.topics.items():
            if topic and topic in normalized_l:
                topics[topic] = max(topics.get(topic, 0.0), 1.0)
                continue
            for term in tp.related_terms[:48]:
                if term and term in normalized_l:
                    topics[topic] = max(topics.get(topic, 0.0), 0.75)
        return topics

    def _tone(self, inf: InferenceState) -> str:
        if inf.threat.label in {"self_harm", "threat"} and inf.threat.confidence >= self._settings.threat_threshold:
            return "safety"

        scores = {"normal": 0.0, "empathy": 0.0}
        if inf.hidden.distress_score >= self._settings.distress_hidden_threshold:
            scores["empathy"] += 0.85
        if inf.sentiment.label == "neg" and inf.sentiment.confidence >= 0.50:
            scores["empathy"] += 0.45
        if inf.sentiment.label == "pos" and inf.hidden.distress_score < 0.35:
            scores["normal"] += 0.25

        # Learned priors: small bias only.
        try:
            pri = (self._policy_priors.get("priors", {}) or {}) if isinstance(self._policy_priors, dict) else {}
            hb = 0
            if inf.hidden.distress_score >= 0.75:
                hb = 3
            elif inf.hidden.distress_score >= 0.62:
                hb = 2
            elif inf.hidden.distress_score >= 0.35:
                hb = 1
            key = f"intent={inf.intent.label}|sent={inf.sentiment.label}|hb={hb}"
            bias = pri.get(key, {}) or {}
            for tone, b in bias.items():
                if tone in scores:
                    scores[tone] += float(b)
        except Exception:
            pass

        return max(scores, key=scores.get)

    def _maybe_proactive(self) -> Optional[Tuple[str, dict]]:
        # Only after some interaction; keep it gentle.
        if self._state.turn_count < 8:
            return None
        gap_turns = self._state.turn_count - self._state.last_proactive_turn
        if gap_turns < self._settings.proactive_min_turn_gap:
            return None
        has_recent = (time.time() - self._state.last_proactive_ts) < self._settings.proactive_min_hours_gap * 3600
        pp = choose_proactive(
            self._memory.semantic,
            min_hours_gap=self._settings.proactive_min_hours_gap,
            has_recent=has_recent,
            style_avg_tokens=self._style.avg_tokens,
        )
        if not pp:
            return None
        self._state.last_proactive_turn = self._state.turn_count
        self._state.last_proactive_ts = time.time()
        return "proactive", {"topic": pp.topic}

    def handle_user_message(self, text: str, client_meta: Optional[dict] = None) -> ChatOutput:
        t0 = time.time()

        # Implicit learning signal from how fast the user came back.
        self._updater.on_user_message()

        self._state.bump_user()
        style_sig = extract_style(self._locale, text)
        self._style.update(style_sig.tokens, style_sig.emojis, style_sig.exclaims, style_sig.questions, style_sig.hedges)
        save_style(self._style_path, self._style)

        hints = None
        if self._governor is not None and getattr(self._events, "enabled", True):
            # Only enforce budgets in normal user mode (admin disables events).
            hints = self._governor.hints_for_user()

        # Retrieve relevant memory for "read between the lines" + continuity.
        if hints is not None and hints.level == "hard":
            retrieved = RetrievedMemory(turns=[], episodes=[], facts=self._memory.semantic.facts)
        else:
            limit_turns = hints.retrieval_limit_turns if hints is not None else 10
            scan_tail = hints.scan_tail_lines if hints is not None else 8000
            retrieved = self._memory.retrieve(text, limit_turns=limit_turns, scan_tail_lines=scan_tail)
        known_facts = retrieved.facts

        inf = InferenceState.from_text(self._locale, text, known_facts=known_facts)

        ctx = make_context(self._locale, inf.normalized)
        brevity = choose_brevity(self._locale, self._style, hidden_distress=inf.hidden.distress_score, user_tokens=len(ctx.tokens_l))

        # Proactive can override tone when user isn't in immediate crisis.
        proactive = None
        allow_proactive = True if hints is None else bool(hints.allow_proactive)
        if allow_proactive and inf.threat.label == "none" and inf.hidden.distress_score < 0.80:
            proactive = self._maybe_proactive()

        tone = proactive[0] if proactive else self._tone(inf)
        slots: Dict[str, str] = {}
        slots["reflect"] = reflect_phrase(inf.sentiment.label, inf.hidden.distress_score, inf.masking.is_masking)
        slots["topic"] = (proactive[1].get("topic") if proactive else "") or self._best_topic(text_l=inf.normalized.lower())

        composed = compose(self._locale, self._updater, tone=tone, brevity=brevity, slots=slots)

        # Optionally add one topic-bound action (skill) when it's appropriate.
        allow_actions = True if hints is None else bool(hints.allow_actions)
        if allow_actions and tone not in {"safety", "proactive"} and brevity in {"short", "normal"}:
            cooldown = int(self._locale.style_rules.get("advice_cooldown_turns", 2))
            if (self._state.turn_count - self._state.last_advice_turn) >= max(1, cooldown) * 2:
                topic = slots.get("topic", "")
                acts = self._knowledge.best_actions(topic, limit=1)
                if acts and inf.intent.label in {"planning", "task", "venting", "question"}:
                    composed = Composed(
                        text=composed.text.rstrip() + " " + f"One small thing you could try: {acts[0]}",
                        template_id=composed.template_id + "+action",
                        tone=composed.tone,
                    )
                    self._state.last_advice_turn = self._state.turn_count

        # Gentle contradiction handling: no accusation; invite clarification.
        if inf.contradiction and inf.contradiction.score >= 0.60 and tone != "safety":
            if brevity == "micro":
                composed = Composed(text="I might be misunderstanding. Can you help me line that up with what you said before?", template_id="system.contradiction_micro", tone="normal")
            else:
                composed = Composed(
                    text="I might be misunderstanding, but this sounds a bit different from what you said earlier. Did something change, or am I reading it wrong?",
                    template_id="system.contradiction",
                    tone="normal",
                )

        shaped = shape_reply(self._locale, self._style, composed.text, target_brevity=brevity, max_chars=self._settings.max_reply_chars)

        # Persist turns + semantic updates
        self._memory.add_turn("user", inf.normalized, meta={"client": client_meta or {}, "inference": self._meta_inference(inf)})
        self._memory.track_episode_turn(inf.normalized, distress_score=inf.hidden.distress_score)

        topic_salience = self._topic_salience(inf.normalized.lower())
        self._memory.update_semantic(claims=inf.claims, topic_salience=topic_salience, distress_score=inf.hidden.distress_score)

        self._memory.add_turn(
            "assistant",
            shaped.text,
            meta={"tone": composed.tone, "template_id": composed.template_id, "brevity": shaped.brevity},
        )
        self._updater.note_response(template_id=composed.template_id, tone=composed.tone)

        self._state.bump_ai(composed.tone, composed.template_id)

        dt_ms = (time.time() - t0) * 1000.0
        self._metrics.observe_chat_latency(dt_ms)
        self._events.publish("dialogue.reply", {"tone": composed.tone, "template_id": composed.template_id, "brevity": shaped.brevity, "latency_ms": dt_ms})

        return ChatOutput(
            reply=shaped.text,
            tone=composed.tone,
            template_id=composed.template_id,
            brevity=shaped.brevity,
            meta={
                "inference": self._meta_inference(inf),
                "retrieved": {
                    "turn_ids": [t.turn_id for t in retrieved.turns],
                    "episodes": retrieved.episodes,
                },
            },
        )

    def _best_topic(self, text_l: str) -> str:
        for phrase in self._locale.lexicons.distress_topics:
            if phrase in text_l:
                return phrase
        for term, sal in sorted(self._memory.semantic.topics.items(), key=lambda kv: kv[1], reverse=True)[:4]:
            if sal >= 0.25:
                return term
        return "that"

    @staticmethod
    def _meta_inference(inf: InferenceState) -> dict:
        return {
            "sentiment": {"label": inf.sentiment.label, "confidence": inf.sentiment.confidence, "score": inf.sentiment.score},
            "intent": {"label": inf.intent.label, "confidence": inf.intent.confidence},
            "sarcasm": {"is_sarcastic": inf.sarcasm.is_sarcastic, "confidence": inf.sarcasm.confidence},
            "threat": {"label": inf.threat.label, "confidence": inf.threat.confidence, "rule_hit": inf.threat.rule_hit},
            "masking": {"is_masking": inf.masking.is_masking, "confidence": inf.masking.confidence, "reasons": inf.masking.reasons},
            "hidden": {"distress_score": inf.hidden.distress_score, "reasons": inf.hidden.reasons},
            "contradiction": (inf.contradiction.__dict__ if inf.contradiction else None),
            "claims": [c.__dict__ for c in inf.claims],
        }
