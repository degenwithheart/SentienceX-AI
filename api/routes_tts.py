from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel, Field

from app.dependencies import get_sx
from app.lifecycle import SentienceX


router = APIRouter()


class TTSRequest(BaseModel):
    text: str = Field(min_length=1, max_length=2000)


@router.post("/tts")
async def tts(body: TTSRequest, sx: SentienceX = Depends(get_sx)) -> Response:
    audio_bytes, media_type = sx.tts.synthesize(body.text)
    if not audio_bytes:
        raise HTTPException(status_code=500, detail="TTS engine unavailable")
    return Response(content=audio_bytes, media_type=media_type)

