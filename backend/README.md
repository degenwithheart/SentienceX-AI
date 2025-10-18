# SentienceX-AI Backend

The backend component of SentienceX-AI is built with FastAPI and provides RESTful API endpoints for conversational AI, real-time analysis, and system management. It integrates machine learning models for sentiment analysis, threat detection, and response generation, along with features like adaptive learning, rate limiting, and monitoring.

## Features

- **Chat API**: Handle user messages and generate AI responses using transformer models.
- **Sentiment Analysis**: Classify text sentiment using BERT-based models.
- **Threat Detection**: Identify potential threats in user inputs.
- **Sarcasm Detection**: Detect sarcastic content.
- **Adaptive Learning**: Adjust model behavior based on user feedback.
- **Self-Monitoring**: Track CPU, memory, and disk usage with logging.
- **Rate Limiting**: Redis-backed token-bucket rate limiting with per-route configuration.
- **Logging and Metrics**: Real-time log streaming and Prometheus metrics.
- **Retraining**: Scheduled or on-demand model retraining with new datasets.
- **Security**: HTTPS enforcement, CORS, trusted hosts, and input sanitization.
- **Audio Synthesis**: Text-to-speech using pyttsx3.

## Requirements

- Python 3.8+
- Dependencies listed in `requirements.txt` (FastAPI, Uvicorn, TensorFlow, Transformers, etc.)
- Redis for rate limiting
- PostgreSQL for data persistence (optional)

## How to Run

### Local Development

1. **Install dependencies**:
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   pip install -r ../requirements.txt
   ```

2. **Set environment variables** (create a `.env` file):
   ```
   MODEL_DEVICE=cpu
   REDIS_URL=redis://localhost:6379/0
   DISABLE_HTTPS_ENFORCEMENT=true
   LOG_ROTATE=true
   ```

3. **Run the server**:
   ```bash
   uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
   ```

4. **With Docker**:
   ```bash
   docker build -t sentiencex-backend .
   docker run -p 8000:8000 -e MODEL_DEVICE=cpu sentiencex-backend
   ```

### Production

Use the root-level docker-compose or deploy with the systemd service in `../deploy/`.

## API Endpoints

- `GET /`: Health check (requires auth).
- `GET /status`: System status and resource metrics.
- `POST /chat/`: Chat endpoint for sending messages and receiving responses.
- `GET /logs/`: Server-sent events for real-time log streaming.
- `POST /retrain/`: Trigger model retraining.
- `GET /ratelimit/keys`: List rate limit keys (admin).
- `DELETE /ratelimit/flush`: Flush rate limit keys (admin).
- `GET /metrics`: Prometheus metrics.

## Configuration

Key environment variables:

- `MODEL_DEVICE`: Inference device (cpu/cuda).
- `REDIS_URL`: Redis connection string.
- `RATE_LIMITS`: JSON config for per-route rate limits.
- `ALLOWED_ORIGINS`: CORS allowed origins.
- `DISABLE_HTTPS_ENFORCEMENT`: Skip HTTPS checks in dev.
- `LOG_ROTATE`: Enable log rotation.
- `SENTIMENT_MODEL`, `THREAT_MODEL`, `RESPONSE_MODEL`: Hugging Face model identifiers.

Models are cached locally in `app/saved_model/`.

## Folder Structure

- `app/`: Main application code.
  - `api/`: API route handlers (chat, retrain, logs, ratelimit).
  - `core/`: Core utilities (model runner, logging).
  - `middleware/`: Security and custom middleware.
  - `dataset/`: Training data (CSV files).
  - `saved_model/`: Cached ML models.
  - `main.py`: FastAPI app entry point.
  - `config.py`: Pydantic settings.
  - `auth.py`: Authentication logic.
  - `adaptive_learning.py`: Feedback-based learning.
  - `self_monitoring.py`: Resource monitoring.
  - `setup_directories.py`: Directory initialization.
- `Dockerfile`: Container build instructions.
- `docker-compose.yml`: Local dev services.
