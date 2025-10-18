import os
import time
import subprocess
import logging
import sys
from fastapi import APIRouter, Header, HTTPException

try:
    import redis as _redis
    _HAS_REDIS = True
except Exception:
    _redis = None
    _HAS_REDIS = False

router = APIRouter()

# cooldown in seconds
RETRAIN_COOLDOWN = int(os.getenv("RETRAIN_COOLDOWN", 300))
RETRAIN_SCRIPT_PATH = os.getenv("RETRAIN_SCRIPT_PATH", "backend/app/retrain_script.py")
AUTH_TOKEN = os.getenv("AUTH_TOKEN")

logging.basicConfig(level=logging.INFO)

# optional Redis client
redis_client = None
if _HAS_REDIS and os.getenv("REDIS_HOST"):
    try:
        redis_client = _redis.StrictRedis(host=os.getenv("REDIS_HOST"), port=int(os.getenv("REDIS_PORT", 6379)), db=0)
    except Exception:
        logging.exception("Failed to initialize Redis client; falling back to in-memory cooldown")

# simple in-memory fallback
_last_retrain_time = 0


@router.post("/")
async def retrain_model(authorization: str = Header(None)):
    if AUTH_TOKEN and authorization != f"Bearer {AUTH_TOKEN}":
        logging.warning("Unauthorized access attempt to retrain endpoint.")
        raise HTTPException(status_code=403, detail="Unauthorized access.")

    current_time = time.time()
    try:
        if redis_client:
            last = redis_client.get("last_retrain_time")
            if last and current_time - float(last) < RETRAIN_COOLDOWN:
                return {"msg": "Retrain request denied. Please wait before retraining again."}
            redis_client.set("last_retrain_time", current_time)
        else:
            global _last_retrain_time
            if _last_retrain_time and current_time - _last_retrain_time < RETRAIN_COOLDOWN:
                return {"msg": "Retrain request denied. Please wait before retraining again."}
            _last_retrain_time = current_time

        # run retrain script asynchronously (non-blocking) using the same
        # Python interpreter to avoid PATH issues. Redirect output to log file.
        try:
            log_path = os.getenv("RETRAIN_LOG_PATH", "backend/app/logs/retrain.log")
            os.makedirs(os.path.dirname(log_path), exist_ok=True)
            with open(log_path, "ab") as lf:
                subprocess.Popen([sys.executable, RETRAIN_SCRIPT_PATH], stdout=lf, stderr=lf)
            logging.info(f"Retraining started (background process). Logs -> {log_path}")
        except Exception:
            logging.exception("Failed to start retrain subprocess")
        return {"msg": "Retraining started successfully."}
    except Exception as e:
        logging.exception("Retraining failed")
        raise HTTPException(status_code=500, detail=f"Retraining failed: {str(e)}")
