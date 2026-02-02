from __future__ import annotations

from fastapi import APIRouter, Depends, Response

from app.dependencies import get_sx
from app.lifecycle import SentienceX
from security.dependencies import require_admin


router = APIRouter()


@router.get("/metrics")
async def metrics(_: None = Depends(require_admin), sx: SentienceX = Depends(get_sx)) -> Response:
    return Response(content=sx.metrics.render(), media_type="text/plain; version=0.0.4; charset=utf-8")
