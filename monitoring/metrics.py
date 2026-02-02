from __future__ import annotations

from prometheus_client import Counter, Gauge, Histogram, generate_latest


class Metrics:
    def __init__(self):
        self.chat_requests = Counter("sentiencex_chat_requests_total", "Total chat requests")
        self.chat_latency_ms = Histogram(
            "sentiencex_chat_latency_ms",
            "Chat pipeline latency (ms)",
            buckets=(5, 10, 25, 50, 100, 200, 400, 800, 1500, 3000, 6000),
        )
        self.cpu_percent = Gauge("sentiencex_cpu_percent", "CPU percent")
        self.mem_rss_mb = Gauge("sentiencex_mem_rss_mb", "Resident memory (MB)")
        self.mem_percent = Gauge("sentiencex_mem_percent", "System memory percent")
        self.temp_c = Gauge("sentiencex_temp_c", "Temperature (C)")
        self.gpu_util_percent = Gauge("sentiencex_gpu_util_percent", "GPU utilization percent")
        self.gpu_temp_c = Gauge("sentiencex_gpu_temp_c", "GPU temperature (C)")

    def observe_chat_latency(self, ms: float) -> None:
        self.chat_requests.inc()
        self.chat_latency_ms.observe(float(ms))

    def set_resources(
        self,
        cpu_percent: float,
        rss_mb: float,
        mem_percent: float | None = None,
        temp_c: float | None = None,
        gpu_util_percent: float | None = None,
        gpu_temp_c: float | None = None,
    ) -> None:
        self.cpu_percent.set(float(cpu_percent))
        self.mem_rss_mb.set(float(rss_mb))
        if mem_percent is not None:
            self.mem_percent.set(float(mem_percent))
        if temp_c is not None:
            self.temp_c.set(float(temp_c))
        if gpu_util_percent is not None:
            self.gpu_util_percent.set(float(gpu_util_percent))
        if gpu_temp_c is not None:
            self.gpu_temp_c.set(float(gpu_temp_c))

    def render(self) -> bytes:
        return generate_latest()
