# SentienceX-AI

Single-user, long-term companion AI built from lightweight symbolic + statistical components.

**Design constraints**
- No transformers, no embeddings, no tokenizers, no HuggingFace
- Runs locally on modest hardware (~1 core / ~1GB) via small linear classifiers + rules
- Streaming/incremental training only (no large datasets loaded into memory)
- One user, one device, persistent memory on disk

## What it does
- Local NLP pipeline: normalization + segmentation + sentence splitting + numeric features
- Lightweight classifiers: intent, sentiment, sarcasm, threat (dot-products from `models/*.json`)
- Cognitive layer: hidden distress + masking signals + soft contradiction detection
- Memory: STM + episodic summaries + semantic facts/topics + inverted index retrieval
- Proactive support: gentle check-ins based on trends/unresolved topics
- Learning: template ranking + tone preference + weak-label self-learning + supervised retraining from `TRAIN/`
- Monitoring: CPU/RAM (+ best-effort GPU/temp), Prometheus metrics, health endpoint
- Security model: single user (no account) + separate admin (system commands only)

## Quick start (backend)

### Requirements
- Python 3.11+ recommended
- Optional: Redis (rate limiting)
- Optional: `say` (macOS) or `espeak` (Linux) for offline TTS
- Optional: `nvidia-smi` (for GPU util/temp metrics if you have Nvidia)

### Run
```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

export SENTIENCEX_DATA_DIR="$(pwd)/data"
uvicorn app.main:app --reload --port 8000
```

On first run the backend creates an admin record at `data/admin.json` and prints an admin token once (save it).

Environment variables are optional; see `.env.example` for the full list (all settings are prefixed with `SENTIENCEX_`).

## Frontend (Next.js)
```bash
cd frontend
npm install
npm run dev
```

Set `NEXT_PUBLIC_API_BASE=http://localhost:8000` (or copy `frontend/.env.local.example` to `frontend/.env.local`).

The UI is glassmorphism with Light/Dark mode, mobile-first responsive layout, and Sonner toasts.

## First-time user setup

The system is designed for **one user**. On first visit, the UI will ask for:
- Name
- DOB (YYYY-MM-DD)
- Location

Saved to `data/user_profile.json` via `PUT /user/profile`.

## Persistence / resume fail-safe

The chat UI persists a compact state locally (for hard refresh survival) and can also resume from the backend:
- Frontend local persistence (best effort) + backend resume fallback: `GET /session/resume`

## Admin (system-level access) — via chat only

Admin is **not the user**. Admin-only actions are executed only when admin mode is enabled.

Enter admin mode in chat:
- `admin:<your_admin_token>`

Exit admin mode:
- `admin:exit` (or `exit`)

Admin mode properties:
- Secure session cookie (HttpOnly), token never stored in the browser
- Admin chat is not persisted to disk and event streaming is disabled
- Auto-exits after 15 seconds of inactivity

Admin-only endpoints (require admin mode):
- `GET /metrics`
- `GET /logs/stream`
- `GET /training/status`
- `POST /training/run`

## Training (streaming + incremental)

All learning consumes text from `TRAIN/` and only writes small artifacts to:
- `models/*.json`
- `cognition/*.json`
- `knowledge/*.json` and `knowledge/actions/*.json`

### TRAIN/ inputs
- `TRAIN/intent/{micro,short,normal}/<label>.txt` (1 phrase per line)
- `TRAIN/sentiment/{micro,short,normal}/<label>.txt`
- `TRAIN/sarcasm/{micro,short,normal}/<label>.txt`
- `TRAIN/threat/{micro,short,normal}/<label>.txt`
- `TRAIN/stories/**/*.txt` (multi-line narratives)
- `TRAIN/topics/<topic>.txt` (terms per line, optional `# sensitivity=0.7`, optional `term|0.8`)
- `TRAIN/skills/<topic>.txt` (advice/steps; imperatives are extracted)
- `TRAIN/raw_conversations/**/*.txt|.jsonl` (user/assistant transcripts)
- `TRAIN/style_samples/user.txt` (your writing samples; emojis allowed here only)

### Run training (admin required)
- `POST /training/run` with body:
  - `{ "modules": ["supervised","stories","topics","skills","conversations","style_bootstrap","weak_labels"], "force_full": false }`
- `GET /training/status`

### Idle training
When the user is inactive for 5 minutes, the scheduler can run training automatically (best-effort, and won’t start if the machine is already very hot).

## Resource governor

Normal user mode is budgeted to avoid exceeding ~50% CPU/RAM by degrading optional work:
- smaller/disabled retrieval
- no proactive prompts
- no added “action” suggestions

Training/admin operations can exceed that budget.

## API endpoints

User:
- `POST /chat`
- `POST /feedback`
- `GET /health`
- `POST /tts`
- `GET /session/resume`
- `GET /user/profile`
- `PUT /user/profile`

Admin-only (unlock via `admin:<token>` in chat):
- `GET /metrics`
- `GET /logs/stream`
- `GET /training/status`
- `POST /training/run`

## Admin key provisioning tool

If you want to set/rotate the admin key without relying on the one-time printed token:
```bash
python tools/admin_key_encrypt.py
```

This writes a one-way PBKDF2 digest to `data/admin.json`.

## Docker
```bash
docker compose up --build
```
