from __future__ import annotations

from typing import Any, Dict

from fastapi import APIRouter, Depends, Query

from app.dependencies import get_sx
from app.lifecycle import SentienceX


router = APIRouter(prefix="/session", tags=["session"])


@router.get("/resume")
async def resume(n: int = Query(default=24, ge=1, le=120), sx: SentienceX = Depends(get_sx)) -> Dict[str, Any]:
    turns = list(sx.memory.stm.iter())[-int(n) :]
    return {
        "turns": [{"turn_id": t.turn_id, "ts": t.ts, "role": t.role, "text": t.text, "meta": t.meta} for t in turns],
        "last_user": next(({"turn_id": t.turn_id, "text": t.text} for t in reversed(turns) if t.role == "user"), None),
        "last_assistant": next(({"turn_id": t.turn_id, "text": t.text} for t in reversed(turns) if t.role == "assistant"), None),
    }

