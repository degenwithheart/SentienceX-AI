from __future__ import annotations

import time
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional

from locale_pack.loader import LocalePack
from training.state import TrainingState

from training.supervised.intent_trainer import train_intent
from training.supervised.sentiment_trainer import train_sentiment
from training.supervised.sarcasm_trainer import train_sarcasm
from training.supervised.threat_trainer import train_threat
from training.stories.story_ingest import run_story_mining
from training.topics.topic_ingest import ingest_topics
from training.topics.topic_profile_builder import build_topic_profiles
from training.skills.skill_ingest import ingest_skills
from training.conversations.raw_ingest import ingest_raw_conversations
from training.conversations.proactive_pattern_miner import mine_proactive_patterns
from training.conversations.policy_prior_updater import update_policy_priors
from training.style.style_bootstrap import bootstrap_style
from training.weak_labels.weak_supervision import build_weak_label_sets


@dataclass(frozen=True)
class TrainingConfig:
    train_dir: Path
    data_dir: Path


class TrainingRunner:
    def __init__(self, locale: LocalePack, cfg: TrainingConfig, state: TrainingState):
        self._locale = locale
        self._cfg = cfg
        self._state = state

    def run(self, modules: Optional[List[str]] = None, force_full: bool = False) -> Dict[str, dict]:
        want = set(modules or [])
        if not want:
            want = {
                "supervised",
                "stories",
                "topics",
                "skills",
                "conversations",
                "style_bootstrap",
                "weak_labels",
            }

        out: Dict[str, dict] = {}

        if "weak_labels" in want:
            out["weak_labels"] = build_weak_label_sets(locale=self._locale, data_dir=self._cfg.data_dir, train_dir=self._cfg.train_dir, state=self._state, force_full=force_full)
            self._state.mark_run("weak_labels")

        if "supervised" in want:
            out["supervised_intent"] = train_intent(locale=self._locale, train_dir=self._cfg.train_dir, data_dir=self._cfg.data_dir, state=self._state, force_full=force_full)
            out["supervised_sentiment"] = train_sentiment(locale=self._locale, train_dir=self._cfg.train_dir, data_dir=self._cfg.data_dir, state=self._state, force_full=force_full)
            out["supervised_sarcasm"] = train_sarcasm(locale=self._locale, train_dir=self._cfg.train_dir, data_dir=self._cfg.data_dir, state=self._state, force_full=force_full)
            out["supervised_threat"] = train_threat(locale=self._locale, train_dir=self._cfg.train_dir, data_dir=self._cfg.data_dir, state=self._state, force_full=force_full)
            self._state.mark_run("supervised")

        if "stories" in want:
            out["stories"] = run_story_mining(locale=self._locale, train_dir=self._cfg.train_dir)
            self._state.mark_run("stories")

        if "topics" in want:
            ing = ingest_topics(locale=self._locale, train_dir=self._cfg.train_dir)
            prof = build_topic_profiles(locale=self._locale, train_dir=self._cfg.train_dir, topics_ingest=ing)
            out["topics"] = {"ingest": ing, "profiles": prof}
            self._state.mark_run("topics")

        if "skills" in want:
            out["skills"] = ingest_skills(locale=self._locale, train_dir=self._cfg.train_dir)
            self._state.mark_run("skills")

        if "conversations" in want:
            conv = ingest_raw_conversations(locale=self._locale, train_dir=self._cfg.train_dir)
            pat = mine_proactive_patterns(locale=self._locale, data_dir=self._cfg.data_dir, conversations=conv)
            pri = update_policy_priors(locale=self._locale, data_dir=self._cfg.data_dir, conversations=conv)
            ingest_public = {k: v for k, v in conv.items() if k != "convs"}
            out["conversations"] = {"ingest": ingest_public, "proactive_patterns": pat, "policy_priors": pri}
            self._state.mark_run("conversations")

        if "style_bootstrap" in want:
            out["style_bootstrap"] = bootstrap_style(locale=self._locale, train_dir=self._cfg.train_dir, data_dir=self._cfg.data_dir)
            self._state.mark_run("style_bootstrap")

        return out
