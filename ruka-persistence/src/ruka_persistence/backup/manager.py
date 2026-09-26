import json
import hashlib
import shutil
from pathlib import Path
import time

class BackupManager:
    def __init__(self, backup_dir: str | Path):
        self.backup_dir = Path(backup_dir)
        self.backup_dir.mkdir(parents=True, exist_ok=True)

    def create_backup(self, source_db: str | Path) -> str:
        src = Path(source_db)
        if not src.exists():
            raise FileNotFoundError()
        
        ts = int(time.time())
        dest = self.backup_dir / f"backup_{ts}.db"
        shutil.copy2(src, dest)
        
        # Manifest
        h = hashlib.sha256(dest.read_bytes()).hexdigest()
        manifest = self.backup_dir / f"manifest_{ts}.json"
        manifest.write_text(json.dumps({"file": dest.name, "hash": h}))
        
        return str(dest)
