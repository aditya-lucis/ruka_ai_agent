import hashlib
import json
from dataclasses import dataclass, field
from pathlib import Path

@dataclass
class PersistentSelf:
    """Dokumen identitas persisten (Part XXI)."""
    identity_name: str
    birth_date: float
    core_directives: list[str] = field(default_factory=list)
    version: int = 1
    
    def generate_hash(self) -> str:
        """Menghasilkan SHA-256 hash dari properti inti."""
        payload = {
            "identity_name": self.identity_name,
            "birth_date": round(self.birth_date, 3),
            "core_directives": sorted(self.core_directives),
            "version": self.version
        }
        text = json.dumps(payload, sort_keys=True)
        return hashlib.sha256(text.encode("utf-8")).hexdigest()

    def verify_hash(self, stored_hash: str) -> bool:
        return self.generate_hash() == stored_hash
        
    def save(self, path: str | Path) -> str:
        h = self.generate_hash()
        data = {
            "identity_name": self.identity_name,
            "birth_date": self.birth_date,
            "core_directives": self.core_directives,
            "version": self.version,
            "hash": h
        }
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        Path(path).write_text(json.dumps(data, indent=2), encoding="utf-8")
        return h

    @classmethod
    def load(cls, path: str | Path) -> tuple["PersistentSelf", bool]:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        stored_hash = data.pop("hash", "")
        obj = cls(**data)
        return obj, obj.verify_hash(stored_hash)
