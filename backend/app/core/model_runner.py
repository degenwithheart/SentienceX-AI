import tensorflow as tf
from transformers import TFDistilBertForSequenceClassification, DistilBertTokenizer
from transformers import TFGPT2LMHeadModel, GPT2Tokenizer
import numpy as np
import pyttsx3
import io
import tempfile

bert_model = TFDistilBertForSequenceClassification.from_pretrained("distilbert-base-uncased-finetuned-sst-2-english")
bert_tokenizer = DistilBertTokenizer.from_pretrained("distilbert-base-uncased")

gpt_model = TFGPT2LMHeadModel.from_pretrained("distilgpt2")
gpt_tokenizer = GPT2Tokenizer.from_pretrained("distilgpt2")

class SentimentAnalysisError(Exception):
    pass

class ThreatDetectionError(Exception):
    pass

class SarcasmDetectionError(Exception):
    pass

def analyze_sentiment(text):
    try:
        if not text or not isinstance(text, str):
            raise ValueError("Invalid input for sentiment analysis.")
        inputs = bert_tokenizer(text, return_tensors="tf", truncation=True, padding=True)
        outputs = bert_model(**inputs)
        scores = tf.nn.softmax(outputs.logits, axis=1).numpy()[0]
        return {"sentiment": {"positive": float(scores[1]), "neutral": float(scores[2]), "negative": float(scores[0])}}
    except Exception as e:
        raise SentimentAnalysisError(f"Error during sentiment analysis: {str(e)}")

def detect_sarcasm(text):
    try:
        if not text or not isinstance(text, str):
            raise ValueError("Invalid input for sarcasm detection.")
        sarcastic_keywords = ["yeah right", "sure", "totally", "obviously"]
        sarcasm_score = sum([text.lower().count(k) for k in sarcastic_keywords]) / len(sarcastic_keywords)
        return {"sarcasm_level": min(sarcasm_score, 1.0)}
    except Exception as e:
        raise SarcasmDetectionError(f"Error during sarcasm detection: {str(e)}")

def detect_threat(text):
    try:
        if not text or not isinstance(text, str):
            raise ValueError("Invalid input for threat detection.")
        keywords = ["kill", "bomb", "attack", "explode", "stab"]
        context_keywords = ["urgent", "immediate", "dangerous", "critical"]
        threat_score = sum([text.lower().count(k) for k in keywords]) / 10.0
        context_score = sum([text.lower().count(k) for k in context_keywords]) / 5.0
        return {"threat_level": min(threat_score + context_score, 1.0)}
    except Exception as e:
        raise ThreatDetectionError(f"Error during threat detection: {str(e)}")

def generate_response(prompt):
    if not prompt or not isinstance(prompt, str):
        raise ValueError("Invalid input for response generation.")
    input_ids = gpt_tokenizer.encode(prompt, return_tensors="tf")
    output = gpt_model.generate(input_ids, max_length=100, num_return_sequences=1)
    return gpt_tokenizer.decode(output[0], skip_special_tokens=True)

def synthesize_audio(text):
    if not text or not isinstance(text, str):
        raise ValueError("Invalid input for audio synthesis.")
    engine = pyttsx3.init()
    with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tf_audio:
        engine.save_to_file(text, tf_audio.name)
        engine.runAndWait()
        tf_audio.seek(0)
        return tf_audio.read()
