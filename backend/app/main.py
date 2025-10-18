import os
from fastapi import FastAPI, WebSocket, Depends
from app.api import chat, retrain, logs
from app.api import ratelimit
from app.auth import get_current_user
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
from app.self_monitoring import SelfMonitoring
from app.adaptive_learning import AdaptiveLearning
from app.core.model_runner import analyze_sentiment, generate_response
from app.setup_directories import create_directories
from app.middleware.security import security_middleware
from app.config import get_settings
from fastapi import Response
try:
    from prometheus_client import generate_latest, CONTENT_TYPE_LATEST
    _HAS_PROM = True
except Exception:
    _HAS_PROM = False

ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "").split(",")

settings = get_settings()

app = FastAPI()

# Attach security middleware (uses settings internally)
app.middleware('http')(security_middleware(app))

self_monitoring = SelfMonitoring()
adaptive_learning = AdaptiveLearning()

# Ensure workspace directories exist (datasets, model cache)
create_directories()

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,  # Restrict origins
    allow_credentials=True,
    allow_methods=["GET", "POST"],  # Restrict methods
    allow_headers=["Authorization", "Content-Type"],  # Restrict headers
)

app.add_middleware(TrustedHostMiddleware, allowed_hosts=["localhost", "127.0.0.1"])

@app.middleware("http")
async def enforce_https(request, call_next):
    # Allow disabling HTTPS enforcement for local development
    if settings.DISABLE_HTTPS_ENFORCEMENT:
        return await call_next(request)
    if request.url.scheme != "https":
        return JSONResponse(
            status_code=403,
            content={"detail": "HTTPS is required for security."}
        )
    return await call_next(request)

@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    return JSONResponse(
        status_code=500,
        content={"detail": "An unexpected error occurred."}
    )

app.include_router(chat.router, prefix="/chat")
app.include_router(retrain.router, prefix="/retrain")
app.include_router(logs.router, prefix="/logs")
app.include_router(ratelimit.router, prefix="/ratelimit")


@app.on_event("startup")
def validate_rate_limits():
    # If RATE_LIMITS is provided and strict validation is desired, fail fast on invalid JSON
    settings = get_settings()
    if settings.RATE_LIMITS:
        try:
            import json

            parsed = json.loads(settings.RATE_LIMITS)
            if not isinstance(parsed, dict):
                raise ValueError("RATE_LIMITS must be a JSON object mapping prefixes to configs")
        except Exception as e:
            # If user explicitly wanted strict validation, raise to stop startup
            if getattr(settings, "RATE_LIMITS_STRICT", False):
                raise
            else:
                # log and continue
                import logging

                logging.getLogger(__name__).exception("Invalid RATE_LIMITS JSON; ignoring: %s", e)

@app.get("/", dependencies=[Depends(get_current_user)])
def read_root():
    return {"msg": "SentienceX-AI backend running."}

@app.get("/status")
async def report_status():
    metrics = self_monitoring.monitor_resources()
    self_monitoring.log_metric("resource_usage", metrics)
    anomalies = self_monitoring.anomalies
    predictions = adaptive_learning.predict_user_needs()
    return {
        "metrics": metrics,
        "anomalies": anomalies,
        "feedback_history": adaptive_learning.feedback_history,
        "predictions": predictions
    }

@app.post("/feedback")
async def provide_feedback(key: str, score: float):
    adaptive_learning.provide_feedback(key, score)
    adaptive_learning.adjust_behavior()
    return {"msg": "Feedback processed successfully."}

@app.post("/chat_with_context")
async def chat_with_context(text: str, context: str):
    sentiment = analyze_sentiment(text, context)
    response = generate_response(text, context)
    adaptive_learning.provide_feedback("chat_response", sentiment["sentiment"]["positive"])
    return {"response": response, "sentiment": sentiment}


if settings.ENABLE_METRICS and _HAS_PROM:
    @app.get("/metrics")
    def metrics_endpoint():
        return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)
