from __future__ import annotations

import time
from typing import Any, Dict

from fastapi import APIRouter, Depends

from app.dependencies import get_sx
from app.lifecycle import SentienceX


router = APIRouter()


@router.get("/health")
async def health(sx: SentienceX = Depends(get_sx)) -> Dict[str, Any]:
    snap = sx.resources.snapshot()
    sx.metrics.set_resources(snap.cpu_percent, snap.rss_mb, mem_percent=snap.mem_percent, temp_c=snap.temp_c, gpu_util_percent=snap.gpu_util_percent, gpu_temp_c=snap.gpu_temp_c)
    return {
        "ok": True,
        "uptime_sec": time.time() - sx.started_at,
        "locale": sx.locale.name,
        "memory": {
            "stm_turns": len(list(sx.memory.stm.iter())),
            "facts": len(sx.memory.semantic.facts),
            "topics": len(sx.memory.semantic.topics),
            "episodes": len(sx.memory.episodes.all()),
            "index_docs": sx.memory.index.doc_count,
        },
        "resources": {
            "cpu_percent": snap.cpu_percent,
            "mem_percent": snap.mem_percent,
            "rss_mb": snap.rss_mb,
            "temp_c": snap.temp_c,
            "gpu_util_percent": snap.gpu_util_percent,
            "gpu_temp_c": snap.gpu_temp_c,
        },
    }
