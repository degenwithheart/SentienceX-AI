from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
import secrets
import sys
import time
import hmac
from dataclasses import dataclass
from getpass import getpass
from pathlib import Path


def _b64(b: bytes) -> str:
    return base64.urlsafe_b64encode(b).decode("ascii").rstrip("=")


def _project_root() -> Path:
    return Path(__file__).resolve().parents[1]


@dataclass(frozen=True)
class AdminRecord:
    version: int
    kdf: str
    hash: str
    dklen: int
    created_at: float
    salt_b64: str
    iterations: int
    digest_b64: str

    def to_json(self) -> dict:
        return {
            "version": self.version,
            "kdf": self.kdf,
            "hash": self.hash,
            "dklen": self.dklen,
            "created_at": self.created_at,
            "salt_b64": self.salt_b64,
            "iterations": self.iterations,
            "digest_b64": self.digest_b64,
        }


# ---- Quantum-hardened parameters (still stdlib, still PBKDF2) ----

KDF_NAME = "pbkdf2"
HASH_NAME = "sha512"
DKLEN = 32   # 256-bit derived key


def derive_record(token: str, *, iterations: int) -> AdminRecord:
    token = (token or "").strip()

    # Stronger minimum for post-quantum margin
    if len(token) < 32:
        raise ValueError("Admin token is too short; use at least 32 characters.")

    salt = secrets.token_bytes(16)

    digest = hashlib.pbkdf2_hmac(
        HASH_NAME,
        token.encode("utf-8"),
        salt,
        int(iterations),
        dklen=DKLEN,
    )

    return AdminRecord(
        version=2,
        kdf=KDF_NAME,
        hash=HASH_NAME,
        dklen=DKLEN,
        created_at=time.time(),
        salt_b64=_b64(salt),
        iterations=int(iterations),
        digest_b64=_b64(digest),
    )


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Derive and store a one-way admin key digest (PBKDF2-HMAC-SHA512)."
    )
    ap.add_argument("--data-dir", type=str, default=None, help="Data directory (default: <repo>/data).")
    ap.add_argument("--iterations", type=int, default=400_000, help="PBKDF2 iterations.")
    ap.add_argument("--force", action="store_true", help="Overwrite existing data/admin.json.")
    args = ap.parse_args()

    root = _project_root()
    data_dir = Path(args.data_dir) if args.data_dir else (root / "data")
    data_dir.mkdir(parents=True, exist_ok=True)
    out_path = data_dir / "admin.json"

    if out_path.exists() and not args.force:
        print(f"Refusing to overwrite existing {out_path}. Use --force to overwrite.", file=sys.stderr)
        return 2

    print("Enter your admin key/seed. This will be stored only as a one-way digest.")
    print("Minimum length: 32 characters.")
    token1 = getpass("Admin key: ")
    token2 = getpass("Confirm: ")

    if token1 != token2:
        print("Keys do not match.", file=sys.stderr)
        return 3

    try:
        rec = derive_record(token1, iterations=int(args.iterations))
    except ValueError as e:
        print(str(e), file=sys.stderr)
        return 4

    out_path.write_text(
        json.dumps(rec.to_json(), ensure_ascii=False, indent=2),
        encoding="utf-8"
    )

    print(f"Wrote {out_path}")
    print("Keep your admin key safe; if you lose it, delete admin.json to re-bootstrap.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
