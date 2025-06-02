import logging
from fastapi import APIRouter, Request, HTTPException
from app.core.model_runner import analyze_sentiment, generate_response, detect_threat, synthesize_audio, detect_sarcasm
from app.core.logs import log_conversation
import base64
import html
import asyncio
from contextlib import contextmanager

router = APIRouter()

logging.basicConfig(level=logging.INFO)

@contextmanager
def timeout_context(seconds):
    def timeout_handler(signum, frame):
        raise TimeoutError("Operation timed out.")
    signal.signal(signal.SIGALRM, timeout_handler)
    signal.alarm(seconds)
    try:
        yield
    finally:
        signal.alarm(0)

async def retry_with_timeout(func, retries=3, timeout=5, *args, **kwargs):
    for attempt in range(retries):
        try:
            return await asyncio.wait_for(func(*args, **kwargs), timeout)
        except Exception as e:
            if attempt == retries - 1:
                raise RuntimeError(f"Operation failed after {retries} attempts: {str(e)}")

@router.post("/")
async def chat_endpoint(request: Request):
    try:
        data = await request.json()
        text = data.get("text", "")
        if not text or not isinstance(text, str):
            logging.warning("Invalid input text received.")
            raise HTTPException(status_code=400, detail="Invalid input text.")
        sanitized_text = html.escape(text)  # Sanitize input
        sentiment = await retry_with_timeout(analyze_sentiment, retries=3, timeout=5, sanitized_text)
        threat = await retry_with_timeout(detect_threat, retries=3, timeout=5, sanitized_text)
        reply = await retry_with_timeout(generate_response, retries=3, timeout=10, sanitized_text)
        sarcasm = await retry_with_timeout(detect_sarcasm, retries=3, timeout=5, sanitized_text)
        audio_bytes = await retry_with_timeout(synthesize_audio, retries=3, timeout=10, reply)
        audio_base64 = base64.b64encode(audio_bytes).decode('utf-8')
        log_conversation(sanitized_text, reply, sentiment, threat)
        logging.info(f"Chat processed successfully for input: {sanitized_text}")
        return {
            "response": reply,
            "sentiment": sentiment,
            "threat": threat,
            "sarcasm": sarcasm,
            "audio": audio_base64
        }
    except HTTPException as e:
        logging.error(f"HTTP error during chat processing: {str(e)}")
        raise
    except Exception as e:
        logging.error(f"Unexpected error during chat processing: {str(e)}")
        raise HTTPException(status_code=500, detail="An error occurred while processing the chat.")
