import json
import hashlib
from pathlib import Path
from typing import Any

class AuditStream:
    def __init__(self, log_path: str | Path):
        self.log_path = Path(log_path)
        self.log_path.parent.mkdir(parents=True, exist_ok=True)
        self.last_hash = "0" * 64
        
        # Read last hash if exists
        if self.log_path.exists():
            lines = self.log_path.read_text(encoding="utf-8").strip().split("\n")
            if lines and lines[-1]:
                try:
                    last_record = json.loads(lines[-1])
                    self.last_hash = last_record.get("hash", self.last_hash)
                except Exception:
                    pass

    def append(self, record: dict[str, Any]) -> str:
        record_str = json.dumps(record, sort_keys=True)
        # SHA256(Record_i || Hash_{i-1})
        payload = (record_str + self.last_hash).encode("utf-8")
        current_hash = hashlib.sha256(payload).hexdigest()
        
        entry = {
            "record": record,
            "hash": current_hash,
            "prev_hash": self.last_hash
        }
        
        with open(self.log_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry) + "\n")
            
        self.last_hash = current_hash
        return current_hash
