from __future__ import annotations

from fastapi import Cookie, Header, HTTPException, Request


def require_admin(
    request: Request,
    authorization: str | None = Header(default=None),
    sx_admin: str | None = Cookie(default=None),
) -> None:
    mgr = getattr(request.app.state, "admin_manager", None)
    if mgr is None or not getattr(mgr, "enabled", False):
        raise HTTPException(status_code=503, detail="Admin auth not initialized")

    token = ""
    if authorization:
        parts = authorization.split(" ", 1)
        if len(parts) == 2 and parts[0].lower() == "bearer":
            token = parts[1].strip()

    if token and mgr.verify(token):
        return
    if sx_admin and mgr.verify_session(sx_admin):
        return
    raise HTTPException(status_code=401, detail="Admin auth required")
