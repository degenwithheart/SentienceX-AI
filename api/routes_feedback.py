from __future__ import annotations

from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.dependencies import get_sx
from app.lifecycle import SentienceX


router = APIRouter()


class FeedbackRequest(BaseModel):
    rating: int = Field(ge=-1, le=1)
    template_id: Optional[str] = None
    tone: Optional[str] = None
    note: Optional[str] = Field(default=None, max_length=2000)
    meta: Optional[Dict[str, Any]] = None


@router.post("/feedback")
async def feedback(body: FeedbackRequest, sx: SentienceX = Depends(get_sx)) -> Dict[str, Any]:
    payload = body.model_dump()
    sx.memory.add_feedback({"kind": "explicit", **payload})
    sx.updater.apply_explicit_feedback(payload)
    return {"ok": True}

