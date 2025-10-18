import os
import logging
import json
import datetime
from sqlalchemy import create_engine, Column, String, Float, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import QueuePool

try:
    import pika
    _HAS_PIKA = True
except Exception:
    pika = None
    _HAS_PIKA = False

DATABASE_URL = os.getenv("DATABASE_URL")
RABBITMQ_URL = os.getenv("RABBITMQ_URL")

# Default to a local SQLite DB for development if DATABASE_URL not set
if not DATABASE_URL:
    db_path = os.path.join(os.path.dirname(__file__), "..", "dataset", "logs.db")
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    DATABASE_URL = f"sqlite:///{db_path}"

engine = create_engine(DATABASE_URL, poolclass=QueuePool, pool_size=5, max_overflow=10)
Base = declarative_base()
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Log(Base):
    __tablename__ = "logs"
    id = Column(String, primary_key=True, index=True)
    timestamp = Column(DateTime, default=datetime.datetime.utcnow)
    input = Column(String)
    response = Column(String)
    sentiment_positive = Column(Float)
    sentiment_negative = Column(Float)
    threat_level = Column(Float)


Base.metadata.create_all(bind=engine)


def log_conversation(input_text: str, response_text: str, sentiment: dict, threat: dict):
    db = SessionLocal()
    try:
        # create an id based on timestamp
        entry = Log(
            id=str(datetime.datetime.utcnow().timestamp()).replace('.', ''),
            timestamp=datetime.datetime.utcnow(),
            input=input_text,
            response=response_text,
            sentiment_positive=float(sentiment.get('positive', 0)) if isinstance(sentiment, dict) else 0.0,
            sentiment_negative=float(sentiment.get('negative', 0)) if isinstance(sentiment, dict) else 0.0,
            threat_level=float(threat.get('threat_level', 0)) if isinstance(threat, dict) else 0.0,
        )
        db.add(entry)
        db.commit()

        # optionally publish to RabbitMQ
        if _HAS_PIKA and RABBITMQ_URL:
            try:
                connection = pika.BlockingConnection(pika.URLParameters(RABBITMQ_URL))
                channel = connection.channel()
                channel.queue_declare(queue='logs', durable=True)
                message = json.dumps({
                    'timestamp': entry.timestamp.isoformat(),
                    'input': entry.input,
                    'response': entry.response,
                    'sentiment_positive': entry.sentiment_positive,
                    'sentiment_negative': entry.sentiment_negative,
                    'threat_level': entry.threat_level,
                })
                channel.basic_publish(exchange='', routing_key='logs', body=message)
                connection.close()
            except Exception:
                logging.exception("Failed to publish log to RabbitMQ")
    finally:
        db.close()


def get_recent_logs(limit: int = 100):
    db = SessionLocal()
    try:
        return db.query(Log).order_by(Log.timestamp.desc()).limit(limit).all()
    finally:
        db.close()


def stream_logs_generator(limit: int = 100):
    logs = get_recent_logs(limit)
    for log in logs:
        yield json.dumps({
            'timestamp': log.timestamp.isoformat(),
            'input': log.input,
            'response': log.response,
            'sentiment_positive': log.sentiment_positive,
            'sentiment_negative': log.sentiment_negative,
            'threat_level': log.threat_level,
        }) + "\n"
