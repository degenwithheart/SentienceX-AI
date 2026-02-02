from __future__ import annotations

from typing import List

from fastapi import FastAPI
from starlette.middleware.trustedhost import TrustedHostMiddleware


def add_trusted_hosts(app: FastAPI, allowed: List[str]) -> None:
    if not allowed:
        return
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=allowed)

