from __future__ import annotations

import base64
import hashlib
import hmac
import json
import secrets
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Optional


def _b64(b: bytes) -> str:
    return base64.urlsafe_b64encode(b).decode("ascii").rstrip("=")


def _unb64(s: str) -> bytes:
    pad = "=" * ((4 - (len(s) % 4)) % 4)
    return base64.urlsafe_b64decode((s + pad).encode("ascii"))


@dataclass(frozen=True)
class AdminRecord:
    version: int
    created_at: float
    salt_b64: str
    iterations: int
    digest_b64: str


class AdminManager:
    """
    Admin auth for system-level endpoints.

    - Stores only a one-way PBKDF2-HMAC-SHA256 digest on disk (no plaintext secret).
    - If missing, bootstraps a new admin token and prints it once to stdout.
      Save the token; if lost, delete `data/admin.json` to re-bootstrap.
    """

    def __init__(self, data_dir: Path):
        self._path = data_dir / "admin.json"
        self._record: Optional[AdminRecord] = None
        self._sessions: dict[str, dict] = {}
        self._ensure()

    @property
    def enabled(self) -> bool:
        return self._record is not None

    def _ensure(self) -> None:
        if self._path.exists():
            obj = json.loads(self._path.read_text(encoding="utf-8"))
            self._record = AdminRecord(
                version=int(obj.get("version", 1)),
                created_at=float(obj.get("created_at", 0.0)),
                salt_b64=str(obj["salt_b64"]),
                iterations=int(obj.get("iterations", 220_000)),
                digest_b64=str(obj["digest_b64"]),
            )
            return

        token = _b64(secrets.token_bytes(32))
        salt = secrets.token_bytes(16)
        iterations = 220_000
        digest = hashlib.pbkdf2_hmac("sha256", token.encode("utf-8"), salt, iterations, dklen=32)
        rec = AdminRecord(version=1, created_at=time.time(), salt_b64=_b64(salt), iterations=iterations, digest_b64=_b64(digest))
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._path.write_text(
            json.dumps(
                {"version": rec.version, "created_at": rec.created_at, "salt_b64": rec.salt_b64, "iterations": rec.iterations, "digest_b64": rec.digest_b64},
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
        self._record = rec
        print("\n[SENTIENCEX] Admin token (save this somewhere safe):\n" + token + "\n", flush=True)

    def verify(self, token: str) -> bool:
        if not self._record:
            return False
        token = (token or "").strip()
        if not token:
            return False
        try:
            salt = _unb64(self._record.salt_b64)
            expected = _unb64(self._record.digest_b64)
            got = hashlib.pbkdf2_hmac(
                "sha256",
                token.encode("utf-8"),
                salt,
                int(self._record.iterations),
                dklen=len(expected),
            )
            return hmac.compare_digest(got, expected)
        except Exception:
            return False

    def create_session(self, ttl_sec: int = 15) -> str:
        sid = _b64(secrets.token_bytes(24))
        ttl = max(5, int(ttl_sec))
        self._sessions[sid] = {"exp": time.time() + ttl, "ttl": ttl}
        return sid

    def verify_session(self, sid: str) -> bool:
        sid = (sid or "").strip()
        if not sid:
            return False
        rec = self._sessions.get(sid)
        if rec is None or not isinstance(rec, dict):
            return False
        exp = float(rec.get("exp", 0.0))
        ttl = int(rec.get("ttl", 15))
        if time.time() > exp:
            self._sessions.pop(sid, None)
            return False
        # Sliding expiration (inactivity timer). This is evaluated at request start, so long-running
        # commands won't get kicked mid-request.
        self._sessions[sid] = {"exp": time.time() + max(5, ttl), "ttl": max(5, ttl)}
        return True

    def revoke_session(self, sid: str) -> None:
        sid = (sid or "").strip()
        if sid:
            self._sessions.pop(sid, None)
