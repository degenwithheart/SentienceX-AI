"""Helper to inspect model selection decisions for SentienceX-AI.

This script reads the same environment variables used by the model runner and
prints whether each model will be loaded from a local path or from Hugging Face.
It verifies local directories (if present) and exits with non-zero code when
USE_LOCAL_MODELS is true but required local models are missing.

Usage:
    python backend/app/tools/check_models.py

This prints a short report and returns exit code 0 on success.
"""

import os
import sys
from pathlib import Path

USE_LOCAL = os.getenv("USE_LOCAL_MODELS", "false").lower() in ("1", "true", "yes")
MODEL_CACHE_DIR = Path(os.getenv("MODEL_CACHE_DIR", "backend/app/saved_model"))

MODELS = {
    "sentiment": os.getenv("SENTIMENT_MODEL", "nlptown/bert-base-multilingual-uncased-sentiment"),
    "threat": os.getenv("THREAT_MODEL", "mrm8488/distilbert-base-uncased-finetuned-sentiment"),
    "sarcasm": os.getenv("SARCASM_MODEL", "bert-large-uncased"),
    "response": os.getenv("RESPONSE_MODEL", "gpt2"),
}


def check_model(name: str, model_id: str):
    # candidate local folder
    explicit = Path(model_id)
    sanitized = model_id.replace("/", "_")
    candidate_local = explicit if explicit.is_dir() else (MODEL_CACHE_DIR / f"{sanitized}_{name}")

    if USE_LOCAL:
        if not candidate_local.exists():
            print(f"[ERROR] USE_LOCAL_MODELS=true but local model not found for {name}: {candidate_local}")
            return False
        print(f"[OK] {name}: using local model at {candidate_local}")
        return True

    # if not forced local, prefer local when present
    if candidate_local.exists():
        print(f"[PREF] {name}: local model present at {candidate_local} (will prefer local)")
        return True

    print(f"[FALLBACK] {name}: no local model; will use Hugging Face id '{model_id}' and cache to {MODEL_CACHE_DIR}")
    return True


def main():
    print(f"USE_LOCAL_MODELS={USE_LOCAL}")
    print(f"MODEL_CACHE_DIR={MODEL_CACHE_DIR}")
    ok = True
    for k, v in MODELS.items():
        r = check_model(k, v)
        ok = ok and r

    if not ok:
        print("Model check failed. Place local models or set USE_LOCAL_MODELS=false and allow HF downloads.")
        sys.exit(2)

    print("Model check passed.")


if __name__ == '__main__':
    main()
