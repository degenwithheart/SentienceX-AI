from __future__ import annotations

import datetime as _dt
import random
import time
from dataclasses import dataclass
from threading import Lock
from typing import Callable, Optional

from apscheduler.schedulers.asyncio import AsyncIOScheduler


@dataclass(frozen=True)
class JobIntervals:
    resources_sec: int = 10
    artifacts_sec: int = 20
    updater_sec: int = 60
    compact_min: int = 5
    episode_idle_min: int = 30
    episode_check_sec: int = 60

    idle_train_check_sec: int = 30
    idle_train_after_sec: int = 5 * 60
    idle_train_min_gap_sec: int = 20 * 60


class JobGuard:
    def __init__(self):
        self._lock = Lock()
        self.running: bool = False

    def run(self, fn: Callable[[], None]) -> None:
        if not self._lock.acquire(blocking=False):
            return
        self.running = True
        try:
            fn()
        finally:
            self.running = False
            self._lock.release()


def _safe(policy, name: str, fn: Callable[[], None]) -> None:
    try:
        fn()
    except Exception as e:
        try:
            policy._events.publish("scheduler.error", {"job": name, "error": repr(e)})
        except Exception:
            pass


def register_jobs(
    scheduler: AsyncIOScheduler,
    policy,
    updater,
    store,
    resources,
    *,
    governor=None,
    training=None,
    intervals: Optional[JobIntervals] = None,
) -> None:
    """
    Background maintenance + retraining scheduler.

    Normal user mode should stay under the governor's budget by:
    - skipping non-critical jobs when over budget
    - reducing frequency via job intervals and early-exit checks

    Training/admin operations are allowed to exceed the budget.
    """
    iv = intervals or JobIntervals()
    rng = random.Random(7)
    now = _dt.datetime.now(_dt.timezone.utc)

    guard_compact = JobGuard()
    guard_refresh = JobGuard()
    guard_episode = JobGuard()
    guard_training = JobGuard()
    last_idle_train_at = {"ts": 0.0}

    def _admin_active() -> bool:
        # When admin chat is enabled we disable events; treat that as admin active.
        try:
            return not bool(getattr(policy._events, "enabled", True))
        except Exception:
            return False

    def _over_budget_user() -> bool:
        if governor is None:
            return False
        if _admin_active():
            return False
        try:
            return bool(governor.over_budget_user())
        except Exception:
            return False

    def sample_resources() -> None:
        def run() -> None:
            snap = resources.snapshot()
            policy._metrics.set_resources(
                cpu_percent=snap.cpu_percent,
                rss_mb=snap.rss_mb,
                mem_percent=getattr(snap, "mem_percent", None),
                temp_c=getattr(snap, "temp_c", None),
                gpu_util_percent=getattr(snap, "gpu_util_percent", None),
                gpu_temp_c=getattr(snap, "gpu_temp_c", None),
            )
        _safe(policy, "resources.sample", run)

    def persist_learning() -> None:
        def run() -> None:
            if _over_budget_user():
                return
            updater.save()
        _safe(policy, "learning.save", run)

    def compact() -> None:
        def run() -> None:
            if _over_budget_user():
                return
            store.compact()
            updater.save()
            try:
                policy._events.publish("scheduler.compact", {"doc_count": store.index.doc_count})
            except Exception:
                pass
        guard_compact.run(lambda: _safe(policy, "memory.compact", run))

    def refresh_artifacts() -> None:
        def run() -> None:
            if _over_budget_user():
                return
            if hasattr(policy, "refresh_artifacts"):
                policy.refresh_artifacts()
            # Model hot-reload happens inside inference_state via mtimes; call to ensure cache refresh.
            try:
                from cognition.inference_state import _get_models  # type: ignore
                _get_models()
            except Exception:
                pass
        guard_refresh.run(lambda: _safe(policy, "artifacts.refresh", run))

    def close_episode_if_idle() -> None:
        def run() -> None:
            if _over_budget_user():
                return
            last = float(getattr(store.semantic, "last_turn_ts", 0.0) or 0.0)
            if last <= 0:
                return
            idle_min = (time.time() - last) / 60.0
            if idle_min >= float(iv.episode_idle_min):
                store.maybe_close_episode()
        guard_episode.run(lambda: _safe(policy, "episode.idle_close", run))

    def idle_train() -> None:
        def run() -> None:
            if training is None:
                return
            if _admin_active():
                return
            # Only when user is inactive, and not too frequent.
            last_user = float(getattr(policy.state, "last_user_ts", 0.0) or 0.0)
            if last_user <= 0:
                return
            if (time.time() - last_user) < float(iv.idle_train_after_sec):
                return
            if (time.time() - last_idle_train_at["ts"]) < float(iv.idle_train_min_gap_sec):
                return
            # Don't start if system is already very hot (safety stop, even if training can exceed 50%).
            snap = resources.snapshot()
            if getattr(snap, "cpu_percent", 0.0) >= 85.0:
                return
            if getattr(snap, "mem_percent", 0.0) >= 85.0:
                return

            last_idle_train_at["ts"] = time.time()
            try:
                policy._events.publish("training.idle_start", {})
            except Exception:
                pass
            training.run(modules=None, force_full=False)
            try:
                policy._events.publish("training.idle_done", {})
            except Exception:
                pass

        # Don't overlap with itself.
        if guard_training.running:
            return
        guard_training.run(lambda: _safe(policy, "training.idle", run))

    # Jitter start times so jobs don't align.
    compact_start = int(rng.uniform(5, 20))
    artifacts_start = int(rng.uniform(3, 12))

    scheduler.add_job(
        sample_resources,
        "interval",
        seconds=int(iv.resources_sec),
        id="resources.sample",
        replace_existing=True,
        max_instances=1,
        coalesce=True,
    )
    scheduler.add_job(
        persist_learning,
        "interval",
        seconds=int(iv.updater_sec),
        id="learning.save",
        replace_existing=True,
        max_instances=1,
        coalesce=True,
    )
    scheduler.add_job(
        refresh_artifacts,
        "interval",
        seconds=int(iv.artifacts_sec),
        id="artifacts.refresh",
        replace_existing=True,
        max_instances=1,
        coalesce=True,
        start_date=now + _dt.timedelta(seconds=artifacts_start),
    )
    scheduler.add_job(
        close_episode_if_idle,
        "interval",
        seconds=int(iv.episode_check_sec),
        id="episode.idle_close",
        replace_existing=True,
        max_instances=1,
        coalesce=True,
    )
    scheduler.add_job(
        compact,
        "interval",
        minutes=int(iv.compact_min),
        id="memory.compact",
        replace_existing=True,
        max_instances=1,
        coalesce=True,
        start_date=now + _dt.timedelta(seconds=compact_start),
    )
    scheduler.add_job(
        idle_train,
        "interval",
        seconds=int(iv.idle_train_check_sec),
        id="training.idle",
        replace_existing=True,
        max_instances=1,
        coalesce=True,
    )

