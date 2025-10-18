# SentienceX-AI

SentienceX-AI is an advanced AI-powered chatbot application that provides intelligent conversational responses with real-time analysis capabilities including sentiment detection, threat assessment, sarcasm recognition, and adaptive learning. The application consists of a FastAPI backend handling API endpoints and machine learning models, and a Next.js frontend offering an interactive user interface with data visualizations.

## Features

- **Conversational AI**: Generate context-aware responses using transformer-based language models.
- **Sentiment Analysis**: Analyze user input for positive, negative, and neutral sentiments.
- **Threat Detection**: Identify potential security threats in conversations.
- **Sarcasm Detection**: Recognize sarcastic language patterns.
- **Adaptive Learning**: Continuously improve responses based on user feedback and interaction patterns.
- **Self-Monitoring**: Track system resources, performance metrics, and operational health.
- **Rate Limiting**: Redis-backed token-bucket rate limiting with configurable per-route policies.
- **Real-Time Logging**: Stream conversation logs and analytics data.
- **Audio Synthesis**: Text-to-speech capabilities for audio responses.
- **Retraining**: Scheduled model retraining with new data.
- **Metrics and Monitoring**: Prometheus metrics for request tracking and performance monitoring.
- **Secure Deployment**: HTTPS enforcement, CORS protection, and trusted host middleware.
- **Docker Support**: Containerized deployment with docker-compose for local development.

## Model Information

The application utilizes pre-trained models from Hugging Face for immediate functionality and analysis capabilities while custom local models are being trained and fine-tuned for optimal performance.

## Requirements

- Python 3.8+
- Node.js 16+
- Docker and Docker Compose (for containerized deployment)
- Redis (for rate limiting)
- PostgreSQL (optional, for data persistence)

## How to Run

### Local Development

1. **Clone the repository**:
   ```bash
   git clone https://github.com/degenwithheart/SentienceX-AI-main.git
   cd SentienceX-AI-main
   ```

2. **Set up the backend**:
   ```bash
   cd backend
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   pip install -r ../requirements.txt
   ```

3. **Set up the frontend**:
   ```bash
   cd ../frontend
   npm install
   ```

4. **Run with Docker Compose** (recommended):
   ```bash
   cd ..
   docker-compose up --build
   ```
   This starts the backend, Redis, and Caddy proxy.

5. **Run manually**:
   - Backend: `uvicorn backend.app.main:app --reload --host 0.0.0.0 --port 8000`
   - Frontend: `cd frontend && npm run dev`

6. **Access the application**:
   - Frontend: http://localhost:3000
   - Backend API: http://localhost:8000 (or https://localhost via Caddy)

### Production Deployment

1. Build and run with Docker:
   ```bash
   docker build -t sentiencex-ai .
   docker run -p 8000:8000 sentiencex-ai
   ```

2. Use the provided systemd service file in `deploy/` for system deployment.

3. Configure environment variables for production settings (see backend README).

## Folder Structure

- `app/`: Next.js application pages and layout files.
- `backend/`: Python FastAPI backend code, including API endpoints, models, and utilities.
- `components/`: Reusable React components for the frontend, such as sentiment graphs and threat panels.
- `deploy/`: Deployment configurations, including systemd service files and Caddy proxy setup.
- `frontend/`: Frontend-specific files and configurations.
- `types/`: TypeScript type definitions.

## Configuration

Environment variables are used for configuration. Key variables include:

- `MODEL_DEVICE`: Device for model inference (cpu/gpu).
- `REDIS_URL`: Redis connection URL for rate limiting.
- `ALLOWED_ORIGINS`: Comma-separated list of allowed CORS origins.
- `DISABLE_HTTPS_ENFORCEMENT`: Disable HTTPS requirements for development.

See `backend/README.md` for detailed configuration options.

## API Endpoints

- `POST /api/chat`: Send a message and receive AI response with analysis.
- `GET /api/logs`: Stream real-time conversation logs.
- `POST /api/retrain`: Trigger model retraining.
- `GET /api/ratelimit/keys`: Admin endpoint for rate limit inspection.
- `GET /metrics`: Prometheus metrics endpoint.

## Additional Documentation

- **[Backend README](backend/README.md)**: Comprehensive guide to the FastAPI backend, including detailed setup instructions, API endpoint documentation, configuration options, and machine learning model details.
- **[Frontend README](frontend/README.md)**: Complete overview of the Next.js frontend, covering development setup, component architecture, UI features, and real-time data visualization.

## Contributing

1. Fork the repository.
2. Create a feature branch.
3. Make your changes and test thoroughly.
4. Submit a pull request.

## License

See `LICENSE` file for details.
