from __future__ import annotations

from fastapi import FastAPI

from api.routes_chat import router as chat_router
from api.routes_feedback import router as feedback_router
from api.routes_logs import router as logs_router
from api.routes_metrics import router as metrics_router
from api.routes_tts import router as tts_router
from api.routes_training import router as training_router
from api.routes_user import router as user_router
from api.routes_session import router as session_router
from app.config import get_settings
from app.lifecycle import shutdown_system, startup_system
from monitoring.health import router as health_router
from security.cors import add_cors
from security.rate_limit import RateLimiter
from security.trusted_host import add_trusted_hosts
from security.admin_auth import AdminManager


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title="SentienceX-AI", version="1.0.0")

    add_trusted_hosts(app, settings.trusted_hosts)
    add_cors(app, settings.cors_origins)

    limiter = RateLimiter(enabled=settings.rate_limit_enabled, rpm=settings.rate_limit_rpm, redis_url=settings.redis_url)
    app.state.rate_limiter = limiter

    @app.on_event("startup")
    async def _startup() -> None:
        app.state.sx = startup_system(settings)
        app.state.admin_manager = AdminManager(settings.data_dir)

    @app.on_event("shutdown")
    async def _shutdown() -> None:
        sx = getattr(app.state, "sx", None)
        if sx is not None:
            await shutdown_system(sx)

    app.include_router(health_router)
    app.include_router(chat_router)
    app.include_router(feedback_router)
    app.include_router(user_router)
    app.include_router(session_router)
    app.include_router(metrics_router)
    app.include_router(logs_router)
    app.include_router(tts_router)
    if settings.training_enabled:
        app.include_router(training_router)

    return app


app = create_app()
