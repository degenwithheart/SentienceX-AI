import os
import logging
from typing import Optional
from fastapi import HTTPException, Security
from fastapi.security.api_key import APIKeyHeader
from app.config import get_settings

logger = logging.getLogger(__name__)

settings = get_settings()

# API key header for simplicity; supports Authorization: Bearer <token> or x-api-key
api_key_header = APIKeyHeader(name="Authorization", auto_error=False)

# Admin-specific header
admin_header = APIKeyHeader(name=settings.ADMIN_HEADER_NAME, auto_error=False)


def _client_ip_from_request(request) -> Optional[str]:
    try:
        return request.client.host
    except Exception:
        return None


def _get_token_from_header(value: Optional[str]) -> Optional[str]:
    if not value:
        return None
    # support 'Bearer <token>' and raw token
    if value.lower().startswith("bearer "):
        return value.split(" ", 1)[1].strip()
    return value.strip()


async def get_current_user(api_key: Optional[str] = Security(api_key_header)):
    token = _get_token_from_header(api_key)
    # If AUTH_TOKEN not configured, allow anonymous (dev mode)
    if not settings.AUTH_TOKEN:
        return {"anonymous": True}
    if not token or token != settings.AUTH_TOKEN:
        raise HTTPException(status_code=403, detail="Unauthorized access")
    return {"user": "admin"}


async def get_admin_user(api_key: Optional[str] = Security(api_key_header)):
    token = _get_token_from_header(api_key)
    # First check admin header
    # note: fastapi Security() only grabs the provided header; admin header is available via dependency injection
    # We'll allow passing admin header via the custom admin_header parameter
    from fastapi import Request

    from fastapi import Depends

    async def _inner_admin(request: Request, admin_key: Optional[str] = Security(admin_header)):
        # IP whitelist check
        ip = _client_ip_from_request(request)
        if settings.ADMIN_IP_WHITELIST and ip:
            allowed_ips = [p.strip() for p in settings.ADMIN_IP_WHITELIST.split(",") if p.strip()]
            if ip in allowed_ips:
                return {"admin": True}

        # check admin header token
        if admin_key:
            admin_token = _get_token_from_header(admin_key)
            if settings.ADMIN_TOKEN and admin_token == settings.ADMIN_TOKEN:
                return {"admin": True}

        # fallback to Authorization header tokens
        if settings.ADMIN_TOKEN and token == settings.ADMIN_TOKEN:
            return {"admin": True}
        if settings.AUTH_TOKEN and token == settings.AUTH_TOKEN:
            # allow AUTH_TOKEN for admin only if ADMIN_TOKEN not set
            if not settings.ADMIN_TOKEN:
                return {"admin": True}

        raise HTTPException(status_code=403, detail="Admin access required")

    return await _inner_admin

