import os
import logging
from fastapi import APIRouter, Header, HTTPException
from fastapi.responses import StreamingResponse
from app.core.logs import SessionLocal, Log
import json

router = APIRouter()
AUTH_TOKEN = os.getenv("AUTH_TOKEN")

logging.basicConfig(level=logging.INFO)

def log_stream():
    db = SessionLocal()
    try:
        logs = db.query(Log).order_by(Log.timestamp.desc()).limit(100).all()
        for log in logs:
            yield json.dumps({
                "timestamp": log.timestamp.isoformat(),
                "input": log.input,
                "response": log.response,
                "sentiment_positive": log.sentiment_positive,
                "sentiment_negative": log.sentiment_negative,
                "threat_level": log.threat_level
            }) + "\n"
    except Exception as e:
        logging.error(f"Error streaming logs: {str(e)}")
        raise
    finally:
        db.close()

@router.get("/")
async def stream_logs(authorization: str = Header(None)):
    if authorization != f"Bearer {AUTH_TOKEN}":
        logging.warning("Unauthorized access attempt to logs endpoint.")
        raise HTTPException(status_code=403, detail="Unauthorized access.")
    try:
        return StreamingResponse(log_stream(), media_type="text/event-stream")
    except Exception as e:
        logging.error(f"Failed to stream logs: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to stream logs.")
