import logging

def configure_logging():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s",
        handlers=[
            logging.FileHandler("backend/app/logs/system.log"),
            logging.StreamHandler()
        ]
    )
