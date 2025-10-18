import os
import time
import subprocess
import logging
from fastapi import APIRouter, Header, HTTPException
from fastapi import APIRouter, Header, HTTPException
router = APIRouter()
last_retrain_time = 0
RETRAIN_COOLDOWN = int(os.getenv("RETRAIN_COOLDOWN", 300))  # Cooldown period in seconds (5 minutes)
RETRAIN_SCRIPT_PATH = os.getenv("RETRAIN_SCRIPT_PATH", "backend/app/retrain_script.py")

logging.basicConfig(level=logging.INFO)

@router.post("/")dis.StrictRedis(host=os.getenv("REDIS_HOST", "localhost"), port=6379, db=0)
async def retrain_model(authorization: str = Header(None)):
    if authorization != f"Bearer {os.getenv('AUTH_TOKEN')}":
async def retrain_model(authorization: str = Header(None)):
    if authorization != f"Bearer {os.getenv('AUTH_TOKEN')}":
        logging.warning("Unauthorized access attempt to retrain endpoint.")
        raise HTTPException(status_code=403, detail="Unauthorized access.")
    last_retrain_time = redis_client.get("last_retrain_time")
    current_time = time.time()
    if last_retrain_time and current_time - float(last_retrain_time) < RETRAIN_COOLDOWN:
        logging.info("Retrain request denied due to cooldown period.")
        return {"msg": "Retrain request denied. Please wait before retraining again."}
    redis_client.set("last_retrain_time", current_time)
    try:
        subprocess.run(["python", RETRAIN_SCRIPT_PATH], check=True)
        logging.info("Retraining started successfully.")
        return {"msg": "Retraining started successfully."}
    except subprocess.CalledProcessError as e:
        logging.error(f"Retraining failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Retraining failed: {str(e)}")
