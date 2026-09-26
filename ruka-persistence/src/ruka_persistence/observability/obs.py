import json
import time

def nearest_rank(data: list[float], percentile: float) -> float:
    if not data: return 0.0
    s = sorted(data)
    idx = int(round(percentile / 100.0 * len(s) + 0.5)) - 1
    idx = max(0, min(idx, len(s) - 1))
    return s[idx]

class StructuredLogger:
    def __init__(self, log_path):
        self.log_path = log_path
        
    def log(self, event: str, **kwargs):
        with open(self.log_path, "a") as f:
            f.write(json.dumps({"ts": time.time(), "event": event, **kwargs}) + "\n")

class MetricsRecorder:
    def __init__(self):
        self.metrics = {}
        
    def record(self, name: str, value: float):
        if name not in self.metrics:
            self.metrics[name] = []
        self.metrics[name].append(value)
        
    def get_percentile(self, name: str, p: float) -> float:
        return nearest_rank(self.metrics.get(name, []), p)
