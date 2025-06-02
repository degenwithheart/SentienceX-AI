import os

DATASET_DIR = os.getenv("DATASET_DIR", "backend/app/dataset")
MODEL_DIR = os.getenv("MODEL_DIR", "backend/app/saved_model")

def create_directories():
    os.makedirs(DATASET_DIR, exist_ok=True)
    os.makedirs(MODEL_DIR, exist_ok=True)
    print(f"Directories created or verified: {DATASET_DIR}, {MODEL_DIR}")

if __name__ == "__main__":
    create_directories()
