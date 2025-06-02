import os
from fastapi import FastAPI, WebSocket, Depends
from app.api import chat, retrain, logs
from app.auth import get_current_user
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
from app.self_monitoring import SelfMonitoring
from app.adaptive_learning import AdaptiveLearning
from app.core.model_runner import analyze_sentiment, generate_response

ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "").split(",")

app = FastAPI()

self_monitoring = SelfMonitoring()
adaptive_learning = AdaptiveLearning()

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
