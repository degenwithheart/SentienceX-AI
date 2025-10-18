# Minimal Dockerfile for SentienceX-AI backend
FROM python:3.11-slim

WORKDIR /app

# system deps for audio/tts and faster pip installs
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libsndfile1 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENV PYTHONUNBUFFERED=1
ENV MODEL_DEVICE=cpu

EXPOSE 8000
CMD ["gunicorn", "-k", "uvicorn.workers.UvicornWorker", "-w", "2", "-b", "0.0.0.0:8000", "backend.app.main:app"]
