from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel, Field

from app.dependencies import get_sx
from app.lifecycle import SentienceX


router = APIRouter()


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=10_000)
    client: Optional[Dict[str, Any]] = None


class ChatResponse(BaseModel):
    reply: str
    tone: str
    template_id: str
    brevity: str
    meta: Dict[str, Any]

def _profile_path(data_dir: Path) -> Path:
    return data_dir / "user_profile.json"


def _admin_reply(text: str, meta: Dict[str, Any] | None = None) -> ChatResponse:
    return ChatResponse(
        reply=text,
        tone="normal",
        template_id="admin.chat",
        brevity="short",
        meta=meta or {"mode": "admin"},
    )


def _handle_admin_command(sx: SentienceX, text: str) -> ChatResponse:
    t = (text or "").strip()
    tl = t.lower()

    if tl in {"help", "?"}:
        return _admin_reply(
            "Commands: help · training status · training run [modules...] · profile · health · admin:exit",
            {"mode": "admin", "admin": {"help": True}},
        )

    if tl.startswith("training status") or tl == "training":
        if sx.training is None:
            return _admin_reply("Training is disabled.", {"mode": "admin"})
        return _admin_reply(json.dumps(sx.training.status(), ensure_ascii=False), {"mode": "admin", "admin": {"training": "status"}})

    if tl.startswith("training run") or tl.startswith("train run"):
        if sx.training is None:
            return _admin_reply("Training is disabled.", {"mode": "admin"})
        rest = t.split("run", 1)[1].strip() if "run" in tl else ""
        modules = None
        if rest:
            # split on commas or spaces
            parts = [p.strip() for p in rest.replace(",", " ").split() if p.strip()]
            modules = parts or None
        res = sx.training.run(modules=modules, force_full=False)
        return _admin_reply(json.dumps(res, ensure_ascii=False), {"mode": "admin", "admin": {"training": "run", "modules": modules or "all"}})

    if tl.startswith("profile"):
        p = _profile_path(sx.settings.data_dir)
        if not p.exists():
            return _admin_reply("No user profile set.", {"mode": "admin"})
        try:
            return _admin_reply(p.read_text(encoding="utf-8"), {"mode": "admin"})
        except Exception:
            return _admin_reply("Profile store unreadable.", {"mode": "admin"})

    if tl == "health":
        snap = sx.resources.snapshot()
        obj = {"cpu_percent": snap.cpu_percent, "rss_mb": snap.rss_mb, "stm_turns": len(list(sx.memory.stm.iter()))}
        return _admin_reply(json.dumps(obj, ensure_ascii=False), {"mode": "admin", "admin": {"health": True}})

    return _admin_reply("Unknown admin command. Type 'help'.", {"mode": "admin", "admin": {"unknown": True}})


@router.post("/chat", response_model=ChatResponse)
async def chat(req: Request, body: ChatRequest, resp: Response, sx: SentienceX = Depends(get_sx)) -> ChatResponse:
    limiter = getattr(req.app.state, "rate_limiter", None)
    if limiter is not None:
        ok = await limiter.allow(req)
        if not ok:
            raise HTTPException(status_code=429, detail="Rate limit exceeded")

    mgr = getattr(req.app.state, "admin_manager", None)
    admin_sid = req.cookies.get("sx_admin")
    admin_active = bool(mgr and admin_sid and mgr.verify_session(admin_sid))

    raw = body.message or ""
    s = raw.strip()
    sl = s.lower()

    # Admin enter/exit via chat: "admin:<token>" / "admin:exit"
    if sl.startswith("admin:"):
        token = s.split(":", 1)[1].strip()
        if token.lower() in {"exit", "logout", "off"}:
            if mgr and admin_sid:
                mgr.revoke_session(admin_sid)
            resp.delete_cookie("sx_admin")
            sx.events.enabled = True
            return ChatResponse(
                reply="Admin mode exited.",
                tone="normal",
                template_id="admin.exit",
                brevity="micro",
                meta={"mode": "user", "admin": {"exited": True}},
            )
        # Never persist or log admin token attempts.
        if mgr is None or not mgr.verify(token):
            return ChatResponse(
                reply="Admin token rejected.",
                tone="normal",
                template_id="admin.reject",
                brevity="micro",
                meta={"mode": "user", "admin": {"enabled": False}},
            )
        sid = mgr.create_session(ttl_sec=15)
        resp.set_cookie("sx_admin", sid, httponly=True, samesite="strict")
        sx.events.enabled = False
        return ChatResponse(
            reply="Admin mode enabled.",
            tone="normal",
            template_id="admin.enable",
            brevity="micro",
            meta={"mode": "admin", "admin": {"enabled": True}},
        )

    # While in admin mode: secure, non-persisted, no logs.
    if admin_active:
        if sl in {"exit", "logout"}:
            if mgr and admin_sid:
                mgr.revoke_session(admin_sid)
            resp.delete_cookie("sx_admin")
            sx.events.enabled = True
            return ChatResponse(
                reply="Admin mode exited.",
                tone="normal",
                template_id="admin.exit",
                brevity="micro",
                meta={"mode": "user", "admin": {"exited": True}},
            )
        sx.events.enabled = False
        return _handle_admin_command(sx, s)

    # Normal user chat
    sx.events.enabled = True
    out = sx.policy.handle_user_message(body.message, client_meta=body.client or {})
    out_meta = dict(out.meta or {})
    out_meta.setdefault("mode", "user")
    return ChatResponse(reply=out.reply, tone=out.tone, template_id=out.template_id, brevity=out.brevity, meta=out_meta)
