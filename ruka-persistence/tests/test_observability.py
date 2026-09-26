import pytest
from ruka_persistence.observability.obs import nearest_rank, MetricsRecorder, StructuredLogger
import json

def test_nearest_rank():
    data = [15, 20, 35, 40, 50]
    # nearest rank 40% of 5 is 2nd element (20)
    assert nearest_rank(data, 40.0) == 20
    # 100% of 5 is 5th element (50)
    assert nearest_rank(data, 100.0) == 50

def test_metrics_recorder():
    recorder = MetricsRecorder()
    recorder.record("latency", 10.0)
    recorder.record("latency", 20.0)
    recorder.record("latency", 30.0)
    
    assert recorder.get_percentile("latency", 50.0) == 20.0
    
def test_structured_logger(tmp_path):
    log_file = tmp_path / "log.jsonl"
    logger = StructuredLogger(log_file)
    
    logger.log("boot", status="success")
    assert log_file.exists()
    line = log_file.read_text().strip()
    data = json.loads(line)
    
    assert data["event"] == "boot"
    assert data["status"] == "success"
    assert "ts" in data
