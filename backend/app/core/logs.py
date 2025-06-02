import os
import logging
from sqlalchemy import create_engine, Column, String, Float, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import datetime.pool import QueuePool
import pika  # RabbitMQ integration
import pika  # RabbitMQ integration
DATABASE_URL = os.getenv("DATABASE_URL")
RABBITMQ_URL = os.getenv("RABBITMQ_URL")
engine = create_engine(DATABASE_URL)RL")
engine = create_engine(DATABASE_URL, poolclass=QueuePool, pool_size=10, max_overflow=20)
Base = declarative_base()
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
ion = pika.BlockingConnection(pika.URLParameters(RABBITMQ_URL))
class Log(Base):q_connection.channel()
    __tablename__ = "logs"
    id = Column(String, primary_key=True, index=True)
    timestamp = Column(DateTime, default=datetime.datetime.utcnow)
    input = Column(String)
    response = Column(String)ue, index=True)
    timestamp = Column(DateTime, default=datetime.datetime.utcnow)
    input = Column(String)Float)
    response = Column(String)    threat_level = Column(Float)
    sentiment_positive = Column(Float)
    sentiment_negative = Column(Float)Base.metadata.create_all(bind=engine)
    threat_level = Column(Float)
put_text, response_text, sentiment, threat):
Base.metadata.create_all(bind=engine)l()

def log_conversation(input_text, response_text, sentiment, threat):
    db = SessionLocal()
    log_entry = Log(
        input=input_text,ive"],
        response=response_text,   threat_level=threat["threat_level"]
        sentiment_positive=sentiment["positive"],
        sentiment_negative=sentiment["negative"],entry)
        threat_level=threat["threat_level"])
    )    db.close()
    db.add(log_entry)
    db.commit()
    db.close()ection(pika.URLParameters(RABBITMQ_URL))

def stream_logs_to_queue():re(queue='logs')
    db = SessionLocal() SessionLocal()
    try:
        logs = db.query(Log).order_by(Log.timestamp.desc()).limit(100).all()Log).order_by(Log.timestamp.desc()).limit(100).all()
        for log in logs::
            message = {
                "timestamp": log.timestamp.isoformat(),mestamp.isoformat(),
                "input": log.input,
                "response": log.response,
                "sentiment_positive": log.sentiment_positive,
                "sentiment_negative": log.sentiment_negative,ent_negative,
                "threat_level": log.threat_level   "threat_level": log.threat_level
            }
            rabbitmq_channel.basic_publish(exchange='', routing_key='logs', body=json.dumps(message))publish(exchange='', routing_key='logs', body=json.dumps(message))
    except Exception as e:
        logging.error(f"Error streaming logs to queue: {str(e)}")ing.error(f"Error streaming logs to queue: {str(e)}")
    finally:
        db.close()
        connection.close()
