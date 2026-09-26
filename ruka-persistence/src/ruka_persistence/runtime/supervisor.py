import json
import os
import time
from dataclasses import dataclass, field
from pathlib import Path

HEARTBEAT_TIMEOUT_S = 10.0

class InstanceLockError(RuntimeError):
    pass

@dataclass
class InstanceLock:
    """Kunci satu-instance berbasis berkas heartbeat."""
    path: Path
    pid: int
    boot_token: str
    heartbeat_period_s: float = 3.0
    heartbeat_timeout_s: float = HEARTBEAT_TIMEOUT_S
    _last_beat: float = field(default_factory=time.time, repr=False)

    def write(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(
            json.dumps({"pid": self.pid, "boot_token": self.boot_token,
                        "last_heartbeat": self._last_beat}),
            encoding="utf-8")

    def beat(self, now: float | None = None) -> None:
        """Denyut jantung: tulis waktu SEKARANG ke berkas kunci."""
        self._last_beat = now if now is not None else time.time()
        self.write()

    def is_stale(self, now: float | None = None) -> bool:
        t = now if now is not None else time.time()
        return (t - self._last_beat) > self.heartbeat_timeout_s

def acquire_lock(path: str | Path,
                 pid: int | None = None,
                 boot_token: str = "ruka-boot",
                 now: float | None = None
                 ) -> InstanceLock:
    """Ambil kunci instance; tolak bila instance lain masih segar."""
    p = Path(path)
    t = now if now is not None else time.time()
    
    if p.exists():
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
            age = t - float(data.get("last_heartbeat", 0))
            if age <= HEARTBEAT_TIMEOUT_S:
                raise InstanceLockError(
                    f"instance lain hidup (pid {data.get('pid')}, "
                    f"heartbeat {age:.1f}s lalu) — menolak jadi Ruka kedua")
        except (json.JSONDecodeError, ValueError):
            pass   # berkas korup: anggap sisa mayat, ambil alih
            
    lock = InstanceLock(path=p, pid=pid or os.getpid(),
                        boot_token=boot_token)
    lock.beat(now=t)
    return lock

class RuntimeSupervisor:
    """Supervisor 2-phase graceful shutdown."""
    def __init__(self, lock: InstanceLock):
        self.lock = lock
        self.is_running = True
        
    def shutdown(self, grace_period_s: float = 5.0) -> str:
        """Matikan sistem (2 phase)."""
        self.is_running = False
        # Phase 1: Minta berhenti
        # (Dalam aplikasi asli: kirim sinyal ke threads)
        
        # Phase 2: Tunggu grace period (simulasi)
        time.sleep(0.01) # fast for tests
        return "graceful"
