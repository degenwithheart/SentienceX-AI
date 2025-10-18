import tensorflow as tf
from transformers import TFDistilBertForSequenceClassification, DistilBertTokenizer
import os
import schedule
import time
import logging

DATASET_PATH = os.getenv("DATASET_PATH", "backend/app/dataset/dataset.csv")
MODEL_SAVE_PATH = os.getenv("MODEL_SAVE_PATH", "backend/app/saved_model")

logging.basicConfig(level=logging.INFO)

def retrain_model():
    try:
        # Load dataset
        if not os.path.exists(DATASET_PATH):
            raise RuntimeError(f"Dataset not found at {DATASET_PATH}. Please check the path.")
        import pandas as pd
        dataset = pd.read_csv(DATASET_PATH)
        texts = dataset['text'].tolist()
        labels = dataset[['sentiment', 'sarcasm', 'threat']].values

        # Tokenize data
        tokenizer = DistilBertTokenizer.from_pretrained(os.getenv("TOKENIZER_MODEL", "distilbert-base-uncased"))
        inputs = tokenizer(texts, return_tensors="tf", truncation=True, padding=True, max_length=128)
        labels = tf.convert_to_tensor(labels, dtype=tf.float32)

        # Load pre-trained model
        model = TFDistilBertForSequenceClassification.from_pretrained(os.getenv("MODEL_NAME", "distilbert-base-uncased"), num_labels=3)

        # Compile model
        model.compile(optimizer=tf.keras.optimizers.Adam(learning_rate=5e-5),
                      loss=tf.keras.losses.MeanSquaredError(),
                      metrics=["accuracy"])

        # Train model
        model.fit(inputs["input_ids"], labels, batch_size=32, epochs=3)

    # Save model into a timestamped subfolder to avoid accidental overwrite
    timestamp = str(int(time.time()))
    target_dir = os.path.join(MODEL_SAVE_PATH, f"retrained_{timestamp}")
    os.makedirs(target_dir, exist_ok=True)
    model.save_pretrained(target_dir)
    logging.info(f"Model retrained and saved at {target_dir}")
    except Exception as e:
        logging.error(f"Error during retraining: {str(e)}")

def schedule_retraining():
    schedule.every().day.at("02:00").do(retrain_model)  # Retrain daily at 2 AM
    logging.info("Retraining scheduled daily at 2 AM.")

if __name__ == "__main__":
    schedule_retraining()
    while True:
        schedule.run_pending()
        time.sleep(1)
