import logging
from fastapi import APIRouter, Request, HTTPException
from app.core.model_runner import analyze_sentiment, generate_response, detect_threat, synthesize_audio, detect_sarcasm
from app.core.logs import log_conversation
import base64
import html
import asyncio

router = APIRouter()

logging.getLogger("uvicorn.access").setLevel(logging.INFO)


async def retry_with_timeout(func, *args, retries=3, timeout=5, **kwargs):
    """Retry helper that supports sync and async callables with asyncio timeouts."""
    last_exc = None
    for attempt in range(1, retries + 1):
        try:
            if asyncio.iscoroutinefunction(func):
                return await asyncio.wait_for(func(*args, **kwargs), timeout)
            else:
                return await asyncio.wait_for(asyncio.to_thread(func, *args, **kwargs), timeout)
        except asyncio.TimeoutError as e:
            last_exc = e
            logging.warning(f"Timeout (attempt {attempt}/{retries}) for {func.__name__}")
        except Exception as e:
            last_exc = e
            logging.exception(f"Error in {func.__name__} (attempt {attempt}/{retries}): {e}")
        await asyncio.sleep(0.1 * attempt)
    raise RuntimeError(f"Operation {func.__name__} failed after {retries} attempts: {last_exc}")


@router.post("/")
async def chat_endpoint(request: Request):
    try:
        data = await request.json()
        text = data.get("text", "")
        if not text or not isinstance(text, str):
            logging.warning("Invalid input text received.")
            raise HTTPException(status_code=400, detail="Invalid input text.")
        sanitized_text = html.escape(text)  # Sanitize input

        # Run model ops in parallel where possible
        sentiment_task = asyncio.create_task(retry_with_timeout(analyze_sentiment, sanitized_text, retries=3, timeout=8))
        threat_task = asyncio.create_task(retry_with_timeout(detect_threat, sanitized_text, retries=3, timeout=8))
        sarcasm_task = asyncio.create_task(retry_with_timeout(detect_sarcasm, sanitized_text, retries=3, timeout=8))

        # Generate response may take longer; run after or in parallel as needed
        reply = await retry_with_timeout(generate_response, sanitized_text, retries=3, timeout=20)

        sentiment = await sentiment_task
        threat = await threat_task
        sarcasm = await sarcasm_task

        # Audio may be optional; guard errors so chat still returns text
        try:
            audio_bytes = await retry_with_timeout(synthesize_audio, reply, retries=2, timeout=10)
            audio_base64 = base64.b64encode(audio_bytes).decode('utf-8') if audio_bytes else None
        except Exception:
            logging.exception("Audio synthesis failed; returning response without audio")
            audio_base64 = None

        # Normalize sentiment shape: model may return {'sentiment': {...}}
        if isinstance(sentiment, dict) and 'sentiment' in sentiment:
            sentiment_data = sentiment['sentiment']
        else:
            sentiment_data = sentiment

        # log conversation; protect DB/log insertion
        try:
            log_conversation(sanitized_text, reply, sentiment_data, threat)
        except Exception:
            logging.exception("Failed to log conversation; continuing")

        logging.info(f"Chat processed successfully for input: {sanitized_text}")
        return {
            "response": reply,
            "sentiment": sentiment,
            "threat": threat,
            "sarcasm": sarcasm,
            "audio": audio_base64,
        }
    except HTTPException as e:
        logging.error(f"HTTP error during chat processing: {str(e)}")
        raise
    except Exception as e:
        logging.exception(f"Unexpected error during chat processing: {str(e)}")
        raise HTTPException(status_code=500, detail="An error occurred while processing the chat.")
