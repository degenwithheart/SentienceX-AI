from __future__ import annotations

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.dependencies import get_sx
from app.lifecycle import SentienceX
from security.dependencies import require_admin


router = APIRouter(prefix="/training", tags=["training"])


class TrainingRunRequest(BaseModel):
    modules: Optional[List[str]] = Field(
        default=None,
        description="Subset of modules to run (e.g. supervised, stories, topics, skills, conversations, style_bootstrap, weak_labels).",
    )
    force_full: bool = Field(default=False, description="If true, reprocess inputs from the beginning.")


@router.get("/status")
async def status(_: None = Depends(require_admin), sx: SentienceX = Depends(get_sx)) -> Dict[str, Any]:
    if sx.training is None:
        raise HTTPException(status_code=404, detail="Training is disabled")
    return sx.training.status()


@router.post("/run")
async def run(body: TrainingRunRequest, _: None = Depends(require_admin), sx: SentienceX = Depends(get_sx)) -> Dict[str, Any]:
    if sx.training is None:
        raise HTTPException(status_code=404, detail="Training is disabled")
    res = sx.training.run(modules=body.modules, force_full=body.force_full)
    return {"ok": True, "result": res}
