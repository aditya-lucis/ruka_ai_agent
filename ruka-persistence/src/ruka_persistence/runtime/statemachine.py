from enum import Enum
from dataclasses import dataclass, field
import time

class RuntimeStatus(str, Enum):
    """13 keadaan — nilai string agar log/JSON langsung terbaca."""
    OFFLINE = "offline"            # proses tidak ada
    STARTING = "starting"          # proses lahir, kunci instance
    LOADING = "loading"            # baca identitas + konfigurasi
    VERIFYING = "verifying"        # uji kapabilitas + integritas
    RESTORING = "restoring"        # pasang memori + tool registry
    READY = "ready"                # menunggu Bos
    BUSY = "busy"                  # mengeksekusi tugas/agent loop
    IDLE = "idle"                  # lama tanpa input, masih peka
    SLEEPING = "sleeping"          # aktivitas ditanggalkan
    DEGRADED = "degraded"          # hidup tapi cacat — dilaporkan
    RECOVERING = "recovering"      # mencoba pulih (backoff aktif)
    MAINTENANCE = "maintenance"    # backup / migrasi terjadwal
    STOPPING = "stopping"          # dua tahap, sopan lalu tegas

LEGAL_TRANSITIONS: dict[tuple[RuntimeStatus, RuntimeStatus], str] = {
    (RuntimeStatus.OFFLINE, RuntimeStatus.STARTING): "boot",
    (RuntimeStatus.STARTING, RuntimeStatus.LOADING): "mounted",
    (RuntimeStatus.STARTING, RuntimeStatus.STOPPING): "abort",
    (RuntimeStatus.LOADING, RuntimeStatus.VERIFYING): "loaded",
    (RuntimeStatus.LOADING, RuntimeStatus.DEGRADED): "identity_corrupt",
    (RuntimeStatus.VERIFYING, RuntimeStatus.RESTORING): "verified",
    (RuntimeStatus.VERIFYING, RuntimeStatus.DEGRADED): "capability_failed",
    (RuntimeStatus.RESTORING, RuntimeStatus.READY): "restored",
    (RuntimeStatus.RESTORING, RuntimeStatus.DEGRADED): "memory_unmountable",
    (RuntimeStatus.READY, RuntimeStatus.BUSY): "task",
    (RuntimeStatus.BUSY, RuntimeStatus.READY): "done",
    (RuntimeStatus.READY, RuntimeStatus.IDLE): "idle_timeout",
    (RuntimeStatus.IDLE, RuntimeStatus.READY): "input",
    (RuntimeStatus.IDLE, RuntimeStatus.SLEEPING): "sleep",
    (RuntimeStatus.SLEEPING, RuntimeStatus.READY): "wake",
    (RuntimeStatus.READY, RuntimeStatus.DEGRADED): "failure",
    (RuntimeStatus.BUSY, RuntimeStatus.DEGRADED): "failure",
    (RuntimeStatus.IDLE, RuntimeStatus.DEGRADED): "failure",
    (RuntimeStatus.DEGRADED, RuntimeStatus.RECOVERING): "begin_recovery",
    (RuntimeStatus.RECOVERING, RuntimeStatus.READY): "recovered",
    (RuntimeStatus.RECOVERING, RuntimeStatus.DEGRADED): "recovery_failed",
    (RuntimeStatus.DEGRADED, RuntimeStatus.MAINTENANCE): "schedule_maintenance",
    (RuntimeStatus.MAINTENANCE, RuntimeStatus.RECOVERING): "maintenance_done",
    (RuntimeStatus.READY, RuntimeStatus.STOPPING): "exit",
    (RuntimeStatus.BUSY, RuntimeStatus.STOPPING): "exit",
    (RuntimeStatus.IDLE, RuntimeStatus.STOPPING): "exit",
    (RuntimeStatus.SLEEPING, RuntimeStatus.STOPPING): "exit",
    (RuntimeStatus.DEGRADED, RuntimeStatus.STOPPING): "exit",
    (RuntimeStatus.MAINTENANCE, RuntimeStatus.STOPPING): "exit",
    (RuntimeStatus.STOPPING, RuntimeStatus.OFFLINE): "stopped",
}

class IllegalTransition(RuntimeError):
    """Transisi tak dikenal — BUG atau serangan."""
    def __init__(self, src: RuntimeStatus, dst: RuntimeStatus, attempted_via: str = ""):
        self.src, self.dst, self.via = src, dst, attempted_via
        super().__init__(
            f"transisi ilegal {src.value} -> {dst.value}"
            + (f" (via '{attempted_via}')" if attempted_via else "")
        )

@dataclass
class StateEvent:
    ts: float
    kind: str
    from_state: str
    to_state: str
    via: str
    detail: str

class RuntimeStateMachine:
    """Penjaga keadaan tunggal runtime."""
    initial: RuntimeStatus = RuntimeStatus.OFFLINE
    
    def __init__(self):
        self.events: list[StateEvent] = []
        self.entered_at: dict[RuntimeStatus, float] = {}
        self._state: RuntimeStatus = self.initial
        self._rejections: int = 0
        self._clock = time.monotonic
        self.entered_at[self._state] = self._clock()
        
    @property
    def state(self) -> RuntimeStatus:
        return self._state

    @property
    def rejections(self) -> int:
        return self._rejections

    def time_in_state(self, now: float | None = None) -> float:
        t = now if now is not None else self._clock()
        return t - self.entered_at.get(self._state, t)

    def is_operational(self) -> bool:
        """Status yang layak menerima tugas."""
        return self._state in (RuntimeStatus.READY, RuntimeStatus.BUSY,
                               RuntimeStatus.IDLE)

    def snapshot(self) -> dict:
        return {
            "state": self._state.value,
            "operational": self.is_operational(),
            "since": round(self.entered_at.get(self._state, 0.0), 3),
            "seconds_in_state": round(self.time_in_state(), 3),
            "rejections": self._rejections,
        }

    def transition(self, dst: RuntimeStatus, via: str = "",
                   detail: str = "", *, _now: float | None = None
                   ) -> RuntimeStatus:
        """Validasi + jalankan transisi; lempar bila ilegal."""
        key = (self._state, dst)
        legal_via = LEGAL_TRANSITIONS.get(key)
        
        if legal_via is None:
            self._rejections += 1
            self.events.append(StateEvent(
                ts=round(self._clock(), 3), kind="rejected",
                from_state=self._state.value, to_state=dst.value,
                via=via, detail=detail or "transisi tak dikenal"))
            raise IllegalTransition(self._state, dst, via)
            
        # Update state
        self.events.append(StateEvent(
            ts=round(self._clock(), 3), kind="accepted",
            from_state=self._state.value, to_state=dst.value,
            via=via, detail=detail))
            
        self._state = dst
        self.entered_at[self._state] = self._clock()
        return self._state

def boot_sequence(fsm: RuntimeStateMachine,
                  *, identity_ok: bool = True,
                  capabilities_ok: bool = True,
                  memory_ok: bool = True) -> RuntimeStatus:
    """Sekuens cold-boot kanonik (Part XXII + persistent_self)."""
    fsm.transition(RuntimeStatus.STARTING, "boot")
    fsm.transition(RuntimeStatus.LOADING, "mounted")
    
    if not identity_ok:
        fsm.transition(RuntimeStatus.DEGRADED, "identity_corrupt",
                       "hash identitas tidak cocok / dokumen rusak")
        return fsm.state
        
    fsm.transition(RuntimeStatus.VERIFYING, "loaded")
    
    if not capabilities_ok:
        fsm.transition(RuntimeStatus.DEGRADED, "capability_failed",
                       "kapabilitas terdaftar gagal verifikasi")
        return fsm.state
        
    fsm.transition(RuntimeStatus.RESTORING, "verified")
    
    if not memory_ok:
        fsm.transition(RuntimeStatus.DEGRADED, "memory_unmountable",
                       "memori tak terpasang / korupsi terdeteksi")
        return fsm.state
        
    fsm.transition(RuntimeStatus.READY, "restored")
    return fsm.state
