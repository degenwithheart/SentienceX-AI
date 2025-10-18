# Gunicorn configuration for SentienceX-AI
import os
import multiprocessing

workers = int(os.getenv('GUNICORN_WORKERS', multiprocessing.cpu_count() * 2 + 1))
worker_class = 'uvicorn.workers.UvicornWorker'
threads = int(os.getenv('GUNICORN_THREADS', 2))
timeout = int(os.getenv('GUNICORN_TIMEOUT', 120))
keepalive = 5
preload_app = False
