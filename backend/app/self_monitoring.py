import psutil
import logging
import time

class SelfMonitoring:
    def __init__(self):
        self.metrics = {}
        self.anomalies = []

    def log_metric(self, name, value):
        self.metrics[name] = value
        logging.info(f"Metric logged: {name} = {value}")

    def monitor_resources(self):
        cpu_usage = psutil.cpu_percent(interval=1)
        memory_usage = psutil.virtual_memory().percent
        self.detect_anomalies(cpu_usage, memory_usage)
        return {"cpu_usage": cpu_usage, "memory_usage": memory_usage}

    def detect_anomalies(self, cpu_usage, memory_usage):
        if cpu_usage > 90 or memory_usage > 90:
            anomaly = {"cpu_usage": cpu_usage, "memory_usage": memory_usage, "timestamp": time.time()}
            self.anomalies.append(anomaly)
            logging.warning(f"Anomaly detected: {anomaly}")

    def report_metrics(self):
        logging.info(f"Current Metrics: {self.metrics}")
        logging.info(f"Anomalies: {self.anomalies}")
