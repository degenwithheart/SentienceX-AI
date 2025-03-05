import os
import time
import json
import logging
import numpy as np
import tensorflow as tf
import coqui_tts
import speech_recognition as sr
from transformers import pipeline
from datetime import datetime
from collections import deque

# Load AI Models (DistilBERT for Sentiment & DistilGPT for Text Generation)
sentiment_analyzer = pipeline("sentiment-analysis", model="./models/distilbert")
text_generator = pipeline("text-generation", model="./models/distilgpt")

# Setup Logging
logging.basicConfig(filename="logs/sentiencex.log", level=logging.INFO, format="%(asctime)s - %(message)s")

# Memory System (Stores past emotions & interactions)
memory = {
    "mood_trends": deque(maxlen=50),
    "threat_levels": deque(maxlen=50),
    "recent_topics": deque(maxlen=10)
}

# Voice Recognition
recognizer = sr.Recognizer()
def get_voice_input():
    with sr.Microphone() as source:
        print("Listening...")
        audio = recognizer.listen(source)
        try:
            return recognizer.recognize_google(audio)
        except sr.UnknownValueError:
            return None
        except sr.RequestError:
            return None

# AI Response Function
def generate_response(user_input):
    sentiment = sentiment_analyzer(user_input)[0]
    response = text_generator(user_input, max_length=50, num_return_sequences=1)[0]["generated_text"]
    return sentiment, response

# Threat Detection System
def detect_threat(sentiment):
    score = sentiment["score"]
    label = sentiment["label"]
    if label == "NEGATIVE" and score > 0.9:
        return "⚠️ THREAT"
    elif label == "NEGATIVE" and score > 0.75:
        return "🔶 SUSPICIOUS"
    else:
        return "🟡 NORMAL"

# AI Memory Update
def update_memory(user_input, sentiment, threat_level):
    memory["mood_trends"].append((datetime.now(), sentiment["label"]))
    memory["threat_levels"].append((datetime.now(), threat_level))
    memory["recent_topics"].append(user_input[:50])
    with open("memory.json", "w") as f:
        json.dump(memory, f)

# Main Loop
def main():
    print("SentienceX AI is active. Type 'exit' to quit.")
    while True:
        user_input = input("🗣 You: ") or get_voice_input()
        if not user_input:
            continue
        if user_input.lower() == "exit":
            break

        sentiment, response = generate_response(user_input)
        threat_level = detect_threat(sentiment)
        update_memory(user_input, sentiment, threat_level)

        print(f"🔍 Sentiment: {sentiment['label']} (Confidence: {sentiment['score']:.2f})")
        print(f"🚨 Threat Level: {threat_level}")
        print(f"🤖 SentienceX: {response}")

        # Logging
        logging.info(f"User: {user_input} | Sentiment: {sentiment['label']} | Threat: {threat_level} | AI: {response}")
        
        # AI Voice Output (Optional)
        # coqui_tts.speak(response)

if __name__ == "__main__":
    main()
