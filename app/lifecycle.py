from __future__ import annotations

import time
import datetime as _dt
from dataclasses import dataclass

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from app.config import Settings
from cognition.inference_state import InferenceState
from dialogue.policy import DialoguePolicy
from learning.online_update import OnlineUpdater
from locale_pack.loader import LocalePack
from logging.stream import EventBus
from memory.persistence import MemoryStore
from monitoring.governor import ResourceGovernor
from monitoring.metrics import Metrics
from monitoring.resources import ResourceMonitor
from scheduler.retrain import register_jobs
from tts.engine import TTSEngine
from training.router import TrainingOrchestrator
from training.schedule import TrainingConfig


@dataclass
class SentienceX:
    settings: Settings
    locale: LocalePack
    memory: MemoryStore
    policy: DialoguePolicy
    updater: OnlineUpdater
    metrics: Metrics
    resources: ResourceMonitor
    events: EventBus
    tts: TTSEngine
    scheduler: AsyncIOScheduler
    training: TrainingOrchestrator | None
    started_at: float

    def infer(self, text: str) -> InferenceState:
        return InferenceState.from_text(self.locale, text)


def startup_system(settings: Settings) -> SentienceX:
    started_at = time.time()

    events = EventBus()
    locale = LocalePack.load(settings.locale)
    metrics = Metrics()
    resources = ResourceMonitor()
    governor = ResourceGovernor(resources)
    memory = MemoryStore.open(settings.data_dir, locale=locale, stm_turns=settings.stm_turns, events=events)
    updater = OnlineUpdater(store=memory, events=events)
    policy = DialoguePolicy(settings=settings, locale=locale, memory=memory, metrics=metrics, updater=updater, events=events)
    policy.set_governor(governor)
    tts = TTSEngine(locale=locale)

    training = None
    if settings.training_enabled:
        cfg = TrainingConfig(train_dir=settings.training_train_dir, data_dir=settings.data_dir)
        training = TrainingOrchestrator(locale=locale, cfg=cfg)

    scheduler = AsyncIOScheduler()
    register_jobs(scheduler=scheduler, policy=policy, updater=updater, store=memory, resources=resources, governor=governor, training=training)
    scheduler.start()

    if training is not None:
        if settings.training_run_on_startup:
            scheduler.add_job(
                lambda: training.run(modules=None, force_full=False),
                "date",
                run_date=_dt.datetime.now(_dt.timezone.utc) + _dt.timedelta(seconds=2),
                id="training.startup",
                replace_existing=True,
            )
        if settings.training_nightly:
            scheduler.add_job(
                lambda: training.run(modules=None, force_full=False),
                "cron",
                hour=int(settings.training_nightly_hour),
                minute=int(settings.training_nightly_minute),
                id="training.nightly",
                replace_existing=True,
                max_instances=1,
            )

    events.publish(
        "system.startup",
        {"locale": settings.locale, "data_dir": str(settings.data_dir), "started_at": started_at},
    )

    return SentienceX(
        settings=settings,
        locale=locale,
        memory=memory,
        policy=policy,
        updater=updater,
        metrics=metrics,
        resources=resources,
        events=events,
        tts=tts,
        scheduler=scheduler,
        training=training,
        started_at=started_at,
    )


async def shutdown_system(sx: SentienceX) -> None:
    sx.events.publish("system.shutdown", {})
    sx.scheduler.shutdown(wait=False)
    sx.memory.close()
