from __future__ import annotations

from dataclasses import dataclass

import psutil
import subprocess
from typing import Optional, Tuple


@dataclass(frozen=True)
class ResourceSnapshot:
    cpu_percent: float
    mem_percent: float
    rss_mb: float
    temp_c: Optional[float] = None
    gpu_util_percent: Optional[float] = None
    gpu_temp_c: Optional[float] = None


class ResourceMonitor:
    def __init__(self):
        # Prime cpu_percent() so the first reading isn't always 0.
        try:
            psutil.cpu_percent(interval=None)
        except Exception:
            pass

    def _temp_c(self) -> Optional[float]:
        try:
            temps = psutil.sensors_temperatures(fahrenheit=False)
        except Exception:
            return None
        if not temps:
            return None
        best = None
        for _, arr in temps.items():
            for t in arr or []:
                cur = getattr(t, "current", None)
                if cur is None:
                    continue
                try:
                    cur_f = float(cur)
                except Exception:
                    continue
                best = cur_f if best is None else max(best, cur_f)
        return best

    def _gpu(self) -> Tuple[Optional[float], Optional[float]]:
        # Best-effort Nvidia support (Linux/Windows with nvidia-smi).
        try:
            out = subprocess.check_output(
                ["nvidia-smi", "--query-gpu=utilization.gpu,temperature.gpu", "--format=csv,noheader,nounits"],
                stderr=subprocess.DEVNULL,
                timeout=0.6,
            ).decode("utf-8", errors="ignore").strip()
            if not out:
                return None, None
            first = out.splitlines()[0]
            parts = [p.strip() for p in first.split(",")]
            util = float(parts[0]) if parts and parts[0] else None
            temp = float(parts[1]) if len(parts) > 1 and parts[1] else None
            return util, temp
        except Exception:
            return None, None

    def snapshot(self) -> ResourceSnapshot:
        proc = psutil.Process()
        rss_mb = proc.memory_info().rss / (1024 * 1024)
        cpu = psutil.cpu_percent(interval=0.0)
        mem = psutil.virtual_memory().percent
        temp = self._temp_c()
        gpu_u, gpu_t = self._gpu()
        return ResourceSnapshot(cpu_percent=float(cpu), mem_percent=float(mem), rss_mb=float(rss_mb), temp_c=temp, gpu_util_percent=gpu_u, gpu_temp_c=gpu_t)
