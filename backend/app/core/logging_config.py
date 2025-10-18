import logging
import os

def configure_logging():
    log_path = "backend/app/logs/system.log"
    os.makedirs(os.path.dirname(log_path), exist_ok=True)
    # Rotating file handler if requested
    if os.getenv("LOG_ROTATE", "true").lower() in ("1", "true", "yes"):
        from logging.handlers import RotatingFileHandler
        max_bytes = int(os.getenv("LOG_MAX_BYTES", 10 * 1024 * 1024))
        backup_count = int(os.getenv("LOG_BACKUP_COUNT", 5))
        handler = RotatingFileHandler(log_path, maxBytes=max_bytes, backupCount=backup_count)
        handler.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(message)s"))
        logging.getLogger().setLevel(logging.INFO)
        logging.getLogger().addHandler(handler)
        logging.getLogger().addHandler(logging.StreamHandler())
    else:
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s - %(levelname)s - %(message)s",
            handlers=[
                logging.FileHandler(log_path),
                logging.StreamHandler()
            ]
        )
