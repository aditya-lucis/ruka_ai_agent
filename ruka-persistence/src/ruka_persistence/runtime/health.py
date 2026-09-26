import json
import time
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from ruka_persistence.runtime.statemachine import RuntimeStatus, RuntimeStateMachine

class ComponentStatus(str, Enum):
    OK = "ok"
    DEGRADED = "degraded"
    DOWN = "down"

@dataclass
class Component:
    name: str
    status: ComponentStatus
    detail: str = ""
    latency_ms: float | None = None

@dataclass
class BootReport:
    """Artefak boot: tahap, waktu, kegagalan, status akhir."""
    boot_token: str = ""
    started_at: float = 0.0
    finished_at: float = 0.0
    stages: dict[str, float] = field(default_factory=dict)
    failed_gate: str = ""
    failure_detail: str = ""
    final_state: str = RuntimeStatus.OFFLINE.value
    identity_hash: str = ""
    capabilities_verified: int = 0
    capabilities_failed: list[str] = field(default_factory=list)
    memories_restored: int = 0

    @property
    def boot_ms(self) -> float:
        return max(0.0, (self.finished_at - self.started_at) * 1000.0)

    def save(self, path: str | Path) -> None:
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(self.as_dict(), ensure_ascii=False, indent=2), encoding="utf-8")

    @classmethod
    def load(cls, path: str | Path) -> "BootReport":
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})

    def as_dict(self) -> dict:
        return {
            "boot_token": self.boot_token,
            "started_at": round(self.started_at, 3),
            "boot_ms": round(self.boot_ms, 3),
            "stages": {k: round(v, 3) for k, v in self.stages.items()},
            "failed_gate": self.failed_gate,
            "failure_detail": self.failure_detail,
            "final_state": self.final_state,
            "identity_hash": self.identity_hash,
            "capabilities_verified": self.capabilities_verified,
            "capabilities_failed": self.capabilities_failed,
            "memories_restored": self.memories_restored,
        }

@dataclass
class ShutdownReport:
    """Artefak shutdown: sopan/terpaksa + durasi + apa yang disimpan."""
    initiated_at: float = 0.0
    finished_at: float = 0.0
    outcome: str = "graceful"          # graceful | forced | aborted
    grace_period_s: float = 5.0

class RuntimeHealth:
    """Snapshot kesehatan — dibangun ulang tiap putaran."""
    def __init__(self):
        self.liveness: bool = False
        self.readiness: bool = False
        self.state: RuntimeStatus = RuntimeStatus.OFFLINE
        self.components: dict[str, Component] = {}
        self.checked_at: float = time.time()

    def set(self, name: str, status: ComponentStatus,
            detail: str = "", latency_ms: float | None = None) -> None:
        self.components[name] = Component(name, status, detail, latency_ms)

    def _all(self, want: ComponentStatus) -> bool:
        return bool(self.components) and all(
            c.status == want for c in self.components.values())

    def evaluate(self, fsm: RuntimeStateMachine,
                 heartbeat_fresh: bool = True) -> "RuntimeHealth":
        """Hitung ulang liveness/readiness dari komponen + status."""
        self.state = fsm.state
        self.liveness = heartbeat_fresh and any(
            c.status != ComponentStatus.DOWN
            for c in self.components.values()) if self.components else heartbeat_fresh
            
        self.readiness = fsm.is_operational() and self._all(ComponentStatus.OK)
        self.checked_at = time.time()
        return self

    def snapshot(self) -> dict:
        return {
            "liveness": self.liveness,
            "readiness": self.readiness,
            "state": self.state.value,
            "checked_at": round(self.checked_at, 3),
            "components": {
                n: {"status": c.status.value, "detail": c.detail,
                    "latency_ms": (round(c.latency_ms, 3) if c.latency_ms is not None else None)}
                for n, c in self.components.items()},
        }
