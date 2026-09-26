import sqlite3
import threading
import time
from pathlib import Path

# Migrasi sederhana untuk v1 -> v2, lalu akan dikembangkan lebih lanjut di runner
MIGRATIONS = [
    (1, """
    CREATE TABLE IF NOT EXISTS schema_migrations (
        version INTEGER PRIMARY KEY, 
        applied_at REAL
    );
    """)
]

class MemoryStore:
    """Lapisan persistensi memori — ulir-aman, WAL, dengan migrasi.
    Semua penulisan lewat satu kunci ulir (SQLite serialized) dan
    connection per-instance; pembacaan memakai koneksi yang sama
    dengan check_same_thread=False + lock eksplisit.
    """
    def __init__(self, db_path: str | Path, wal: bool = True):
        self.db_path = str(db_path)
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()
        self._conn = sqlite3.connect(self.db_path,
                                     check_same_thread=False,
                                     timeout=10.0)
        self._conn.row_factory = sqlite3.Row

        if wal:
            self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.execute("PRAGMA synchronous=NORMAL")
        self._conn.execute("PRAGMA foreign_keys=ON")
        self._conn.execute("PRAGMA busy_timeout=5000")
        
        self._migrate()

    # ------------------------------------------------------------ migrasi
    def _migrate(self) -> None:
        with self._lock:
            self._conn.execute(
                "CREATE TABLE IF NOT EXISTS schema_migrations ("
                "version INTEGER PRIMARY KEY, applied_at REAL)")
            applied = {r["version"] for r in self._conn.execute(
                "SELECT version FROM schema_migrations")}
            
            for version, sql in MIGRATIONS:
                if version in applied:
                    continue
                self._conn.executescript(sql)
                self._conn.execute(
                    "INSERT INTO schema_migrations VALUES (?, ?)",
                    (version, time.time()))
            self._conn.commit()

    def get_connection(self) -> sqlite3.Connection:
        """Mendapatkan koneksi untuk dibaca/tulis (wajib menggunakan lock _lock untuk penulisan)"""
        return self._conn
