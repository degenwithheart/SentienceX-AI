import os
from fastapi import FastAPI, WebSocket, Depends
from app.api import chat, retrain, logs
from app.auth import get_current_user
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse

ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "").split(",")

app = FastAPI()

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
