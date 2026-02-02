from __future__ import annotations

from fastapi import Request

from app.lifecycle import SentienceX


def get_sx(request: Request) -> SentienceX:
    sx = getattr(request.app.state, "sx", None)
    if sx is None:
        raise RuntimeError("SentienceX system not initialized")
    return sx

