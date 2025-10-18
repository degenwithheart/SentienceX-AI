"""Model runner using locally-hosted Hugging Face BERT-style models.

This module performs lazy downloading (on first use) and local caching of
models under `backend/app/saved_model/`. It exposes the same public API
used by the rest of the application:
- analyze_sentiment(text, context=None) -> {"sentiment": {...}}
- detect_threat(text) -> {"threat_level": float}
- detect_sarcasm(text) -> {"sarcasm_level": float}
- generate_response(prompt, context=None) -> str
- synthesize_audio(text) -> bytes (wav)  -- optional, uses pyttsx3 if available

Design notes:
- The README states this project uses three BERT models (retrained). We'll
  expect three model identifiers (or local directories) via env vars:
  SENTIMENT_MODEL, THREAT_MODEL, RESPONSE_MODEL.
- On first call the model files are downloaded using the HuggingFace
  transformers/snapshot mechanisms and cached. If the environment is
  offline and the models are already cached, inference proceeds normally.
"""

import os
import threading
import tempfile
import time
from typing import Optional
import logging

from pathlib import Path

try:
    # Transformers-heavy imports are optional until first-run; import lazily.
    from transformers import AutoTokenizer, AutoModelForSequenceClassification, AutoModelForCausalLM
    # pipeline function lives in transformers.pipelines but is usually exposed.
    try:
        from transformers import pipeline
    except Exception:
        from transformers.pipelines import pipeline
except Exception:
    AutoTokenizer = None
    AutoModelForSequenceClassification = None
    AutoModelForCausalLM = None
    pipeline = None

try:
    import pyttsx3
except Exception:
    pyttsx3 = None

try:
    import torch
except Exception:
    torch = None

# logger
logger = logging.getLogger(__name__)
if not logger.handlers:
    # simple default handler to ensure logs appear if not configured by the app
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter("[%(asctime)s] %(levelname)s %(name)s: %(message)s"))
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)


class ModelRunnerError(Exception):
    pass


_BASE_DIR = Path(__file__).resolve().parents[2]
# Default save/cache directory for downloaded or stored models
_DEFAULT_SAVED_MODELS = _BASE_DIR / "saved_model"
_DEFAULT_SAVED_MODELS.mkdir(parents=True, exist_ok=True)

# Allow override of cache dir via env
MODEL_CACHE_DIR = Path(os.environ.get("MODEL_CACHE_DIR", str(_DEFAULT_SAVED_MODELS)))
MODEL_CACHE_DIR.mkdir(parents=True, exist_ok=True)

# Environment-configurable model identifiers
SENTIMENT_MODEL = os.environ.get("SENTIMENT_MODEL", "")
THREAT_MODEL = os.environ.get("THREAT_MODEL", "")
SARCASM_MODEL = os.environ.get("SARCASM_MODEL", "")
RESPONSE_MODEL = os.environ.get("RESPONSE_MODEL", "")
MODEL_DEVICE = os.environ.get("MODEL_DEVICE", "cpu")  # cpu or cuda
# Feature flag: if true, require and prefer local model directories instead of
# downloading from Hugging Face. When true the runner will look for local
# folders under MODEL_CACHE_DIR/<model-name> unless the env var points to an
# explicit path.
USE_LOCAL_MODELS = os.environ.get("USE_LOCAL_MODELS", "false").lower() in ("1", "true", "yes")

# Internal caches
_models = {
    "sentiment": None,
    "threat": None,
    "sarcasm": None,
    "response": None,
}
_tokenizers = {"sentiment": None, "threat": None, "sarcasm": None, "response": None}
_locks = {k: threading.Lock() for k in _models.keys()}


def _ensure_transformers_available():
    if AutoTokenizer is None or pipeline is None:
        raise ModelRunnerError(
            "transformers package is required for real model inference. Install requirements.txt and try again."
        )


def _download_and_load(model_name: str, task: str):
    """Download (if needed) and load model and tokenizer for a task.

    task: one of 'sentiment', 'threat', 'response'
    Returns (tokenizer, model_or_pipeline)
    """
    _ensure_transformers_available()


    # Determine where to load models from. If USE_LOCAL_MODELS is True we expect
    # a local directory for the model (either model_name as a path or
    # MODEL_CACHE_DIR/<sanitized_name>), otherwise we load from Hugging Face
    # and use MODEL_CACHE_DIR as the cache_dir for downloads.
    cache_dir = str(MODEL_CACHE_DIR)
    # Unified cache naming: include task suffix to avoid collisions between tasks
    sanitized = f"{model_name.replace('/', '_')}_{task}"
    explicit_local = Path(model_name)

    # decide local path that would be used when preferring local models
    candidate_local = explicit_local if explicit_local.is_dir() else (MODEL_CACHE_DIR / sanitized)

    # Decide whether to use a local model directory.
    # - If USE_LOCAL_MODELS is true, require local path and fail if missing.
    # - If USE_LOCAL_MODELS is false, prefer a local path if it exists, otherwise
    #   fall back to Hugging Face downloads.
    if USE_LOCAL_MODELS:
        if not candidate_local.exists():
            raise ModelRunnerError(
                f"USE_LOCAL_MODELS is true but local model path not found for '{model_name}': {candidate_local}"
            )
        use_local = True
    else:
        use_local = candidate_local.exists()

    if use_local:
        logger.info(f"[ModelRunner] Using local model for {task}: {candidate_local}")
    else:
        logger.info(f"[ModelRunner] Using Hugging Face model for {task}: {model_name}")

    # Use Hugging Face pipeline helpers for sequence-classification tasks
    if task in ("sentiment", "threat", "sarcasm"):
        try:
            if use_local:
                # prefer local model directory
                pipe = pipeline(
                    "sentiment-analysis",
                    model=str(candidate_local),
                    tokenizer=str(candidate_local),
                    device=0 if MODEL_DEVICE == "cuda" else -1,
                    cache_dir=cache_dir,
                    local_files_only=True,
                )
            else:
                pipe = pipeline(
                    "sentiment-analysis",
                    model=model_name,
                    device=0 if MODEL_DEVICE == "cuda" else -1,
                    cache_dir=cache_dir,
                )
            return None, pipe
        except Exception as e:
            raise ModelRunnerError(f"Failed to load sequence classification pipeline for {model_name}: {e}")

    if task == "response":
        try:
            # For response generation, load causal LM (tokenizer+model) from local or HF
            if use_local:
                tokenizer = AutoTokenizer.from_pretrained(str(candidate_local), cache_dir=cache_dir, local_files_only=True)
                model = AutoModelForCausalLM.from_pretrained(str(candidate_local), cache_dir=cache_dir, local_files_only=True)
            else:
                tokenizer = AutoTokenizer.from_pretrained(model_name, cache_dir=cache_dir)
                model = AutoModelForCausalLM.from_pretrained(model_name, cache_dir=cache_dir)
            return tokenizer, model
        except Exception as e:
            raise ModelRunnerError(f"Failed to load response model {model_name}: {e}")

    raise ModelRunnerError(f"Unknown task: {task}")


def _get_or_load(task: str):
    """Load the model/pipeline for a named task, with lazy download and thread-safety."""
    if task not in _models:
        raise ModelRunnerError(f"Unknown task requested: {task}")

    if _models[task] is not None:
        return _tokenizers.get(task), _models[task]

    with _locks[task]:
        if _models[task] is not None:
            return _tokenizers.get(task), _models[task]

        # choose model name from envs (fallback to README-stated defaults if blank)
        if task == "sentiment":
            name = SENTIMENT_MODEL or "nlptown/bert-base-multilingual-uncased-sentiment"
        elif task == "threat":
            name = THREAT_MODEL or "mrm8488/distilbert-base-uncased-finetuned-sentiment"
        elif task == "sarcasm":
            name = SARCASM_MODEL or "bert-large-uncased"
        elif task == "response":
            name = RESPONSE_MODEL or "gpt2"
        else:
            raise ModelRunnerError(f"Unsupported task: {task}")

        tokenizer, model_or_pipe = _download_and_load(name, task)

        _tokenizers[task] = tokenizer
        _models[task] = model_or_pipe
        return tokenizer, model_or_pipe


def analyze_sentiment(text: str, context: Optional[str] = None):
    if not text or not isinstance(text, str):
        raise ModelRunnerError("Invalid input for sentiment analysis")
    tokenizer, pipe = _get_or_load("sentiment")
    try:
        # pipeline returns label and score; normalize to positive/negative/neutral
        res = pipe(text)
        # handle single output or list
        entry = res[0] if isinstance(res, list) else res
        label = entry.get("label", "NEUTRAL").upper()
        score = float(entry.get("score", 0.0))
        if label.startswith("POS") or label in ("POSITIVE", "5 stars"):
            positive = score
            negative = 1.0 - score
        elif label.startswith("NEG") or label in ("NEGATIVE", "1 star"):
            negative = score
            positive = 1.0 - score
        else:
            # unknown mapping -> map to neutral
            positive = 0.5 * score
            negative = 0.5 * score

        # optional context nudging
        if context and "angry" in context.lower():
            negative = min(1.0, negative + 0.05)

        return {"sentiment": {"positive": float(positive), "neutral": 0.0, "negative": float(negative)}}
    except Exception as e:
        raise ModelRunnerError(f"Sentiment analysis failed: {e}")


def detect_sarcasm(text: str):
    # Use a dedicated sarcasm sequence-classification model/pipeline.
    if not text or not isinstance(text, str):
        raise ModelRunnerError("Invalid input for sarcasm detection")
    try:
        tokenizer, pipe = _get_or_load("sarcasm")
        res = pipe(text)
        entry = res[0] if isinstance(res, list) else res
        score = float(entry.get("score", 0.0))
        label = entry.get("label", "").lower()
        # If the trained model uses labels like 'SARCASM' or 'SARCASTIC', map directly.
        if "sar" in label or "sarcast" in label:
            val = score
        else:
            # If model labels are generic, treat positive scores as higher sarcasm
            val = score * 0.5
        return {"sarcasm_level": float(min(val, 1.0))}
    except Exception as e:
        raise ModelRunnerError(f"Sarcasm detection failed: {e}")


def detect_threat(text: str):
    if not text or not isinstance(text, str):
        raise ModelRunnerError("Invalid input for threat detection")
    try:
        tokenizer, pipe = _get_or_load("threat")
        res = pipe(text)
        entry = res[0] if isinstance(res, list) else res
        score = float(entry.get("score", 0.0))
        # Map positive/negative to threat level heuristically
        label = entry.get("label", "").upper()
        if "THREAT" in label or "DANGER" in label or "NEG" in label:
            threat_level = score
        else:
            threat_level = score * 0.1
        return {"threat_level": float(min(threat_level, 1.0))}
    except Exception as e:
        raise ModelRunnerError(f"Threat detection failed: {e}")


def generate_response(prompt: str, context: Optional[str] = None):
    if not prompt or not isinstance(prompt, str):
        raise ModelRunnerError("Invalid input for response generation")
    try:
        tokenizer, model = _get_or_load("response")
        if tokenizer is None or model is None:
            raise ModelRunnerError("Response model is not available")

        # simple generate with small max length; callers can extend for streaming
        input_text = prompt if not context else f"Context: {context}\nUser: {prompt}"
        inputs = tokenizer.encode(input_text, return_tensors="pt")
        # auto-detect CUDA if requested
        device_to_use = MODEL_DEVICE
        if MODEL_DEVICE == "auto" and torch is not None:
            device_to_use = "cuda" if torch.cuda.is_available() else "cpu"

        if device_to_use == "cuda" and torch is not None:
            try:
                model = model.to("cuda")
                inputs = inputs.to("cuda")
            except Exception:
                logger.warning("Requested CUDA but failed to move model/inputs to GPU; falling back to CPU")

        # Use top-k/top-p sampling for more natural responses
        if torch is not None:
            with torch.no_grad():
                outputs = model.generate(inputs, max_length=inputs.shape[-1] + 100, do_sample=True, top_p=0.92, top_k=50, temperature=0.9)
        else:
            outputs = model.generate(inputs, max_length=inputs.shape[-1] + 100, do_sample=True, top_p=0.92, top_k=50, temperature=0.9)
        text = tokenizer.decode(outputs[0], skip_special_tokens=True)
        # Trim to remove prompt echo if present
        if text.startswith(input_text):
            text = text[len(input_text):].strip()
        return text
    except Exception as e:
        raise ModelRunnerError(f"Response generation failed: {e}")


def synthesize_audio(text: str) -> bytes:
    if not text or not isinstance(text, str):
        raise ModelRunnerError("Invalid input for audio synthesis")
    if pyttsx3 is None:
        logger.warning("pyttsx3 not installed; synthesize_audio will return empty bytes. Install pyttsx3 for audio support.")
        return b""

    engine = pyttsx3.init()
    with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tf_audio:
        engine.save_to_file(text, tf_audio.name)
        engine.runAndWait()
        tf_audio.flush()
        tf_audio.seek(0)
        data = tf_audio.read()
    return data

