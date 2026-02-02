from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any, Dict

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.dependencies import get_sx
from app.lifecycle import SentienceX


router = APIRouter(prefix="/user", tags=["user"])


class UserProfile(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    dob: str = Field(min_length=4, max_length=10, description="YYYY-MM-DD")
    location: str = Field(min_length=1, max_length=120)


def _profile_path(data_dir: Path) -> Path:
    return data_dir / "user_profile.json"


@router.get("/profile")
async def get_profile(sx: SentienceX = Depends(get_sx)) -> Dict[str, Any]:
    p = _profile_path(sx.settings.data_dir)
    if not p.exists():
        return {"exists": False}
    try:
        obj = json.loads(p.read_text(encoding="utf-8"))
        return {"exists": True, "profile": obj.get("profile", {})}
    except Exception:
        raise HTTPException(status_code=500, detail="Profile store corrupted")


@router.put("/profile")
async def put_profile(body: UserProfile, sx: SentienceX = Depends(get_sx)) -> Dict[str, Any]:
    dob = body.dob.strip()
    if not (len(dob) == 10 and dob[4] == "-" and dob[7] == "-"):
        raise HTTPException(status_code=422, detail="dob must be YYYY-MM-DD")
    p = _profile_path(sx.settings.data_dir)
    payload = {"updated_at": time.time(), "profile": body.model_dump()}
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    return {"ok": True}

