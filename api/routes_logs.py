from __future__ import annotations

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse

from app.dependencies import get_sx
from app.lifecycle import SentienceX
from security.dependencies import require_admin


router = APIRouter()


@router.get("/logs/stream")
async def stream_logs(_: None = Depends(require_admin), sx: SentienceX = Depends(get_sx)) -> StreamingResponse:
    async def gen():
        async for ev in sx.events.subscribe():
            yield ev.to_sse()

    return StreamingResponse(gen(), media_type="text/event-stream")
