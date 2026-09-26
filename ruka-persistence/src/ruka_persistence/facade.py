import time
from pathlib import Path
from ruka_persistence.runtime.statemachine import RuntimeStateMachine, RuntimeStatus, boot_sequence
from ruka_persistence.runtime.supervisor import acquire_lock, RuntimeSupervisor, InstanceLockError
from ruka_persistence.runtime.health import RuntimeHealth, ComponentStatus, BootReport, ShutdownReport
from ruka_persistence.selfmodel.self import PersistentSelf
from ruka_persistence.memory.store import MemoryStore
from ruka_persistence.memory.types import SemanticFact
from ruka_persistence.tools.path_jail import PathJail
from ruka_persistence.tools.gateway import IOGateway

class RukaPersistentMind:
    """Fasad utama yang mengorkestrasi semua subsistem."""
    
    def __init__(self, base_dir: str | Path):
        self.base_dir = Path(base_dir).resolve()
        self.fsm = RuntimeStateMachine()
        self.health = RuntimeHealth()
        self.supervisor = None
        self.memory = None
        self.identity = None
        self.io_gateway = None

    def boot(self, identity_path: str | Path, boot_token: str = "ruka-boot") -> BootReport:
        """Memulai runtime Ruka."""
        start_time = time.time()
        report = BootReport(boot_token=boot_token, started_at=start_time)
        
        # 1. Lock & Supervisor
        lock_path = self.base_dir / "runtime" / "heartbeat.json"
        try:
            lock = acquire_lock(lock_path, boot_token=boot_token)
            self.supervisor = RuntimeSupervisor(lock)
        except InstanceLockError as e:
            report.failed_gate = "lock"
            report.failure_detail = str(e)
            report.finished_at = time.time()
            return report
            
        # 2. Identity
        try:
            self.identity, id_ok = PersistentSelf.load(identity_path)
            if id_ok:
                report.identity_hash = self.identity.generate_hash()
        except Exception as e:
            id_ok = False
            report.failure_detail = str(e)

        # 3. Memory
        try:
            db_path = self.base_dir / "memory" / "ruka.db"
            db_path.parent.mkdir(parents=True, exist_ok=True)
            self.memory = MemoryStore(str(db_path))
            mem_ok = True
        except Exception as e:
            mem_ok = False
            if not id_ok:
                report.failure_detail += f" | {e}"
            else:
                report.failure_detail = str(e)
                
        # 4. IO Gateway
        jail = PathJail(self.base_dir)
        self.io_gateway = IOGateway(jail)

        # Execute sequence
        final_state = boot_sequence(
            self.fsm,
            identity_ok=id_ok,
            capabilities_ok=True,
            memory_ok=mem_ok
        )
        
        report.final_state = final_state.value
        report.finished_at = time.time()
        
        report_path = self.base_dir / "runtime" / "boot_report.json"
        report.save(report_path)
        
        return report

    def shutdown(self) -> ShutdownReport:
        """Mematikan runtime secara graceful."""
        init_time = time.time()
        
        if self.supervisor:
            outcome = self.supervisor.shutdown()
        else:
            outcome = "aborted"
            
        try:
            if self.fsm.is_operational():
                self.fsm.transition(RuntimeStatus.STOPPING, "exit")
            self.fsm.transition(RuntimeStatus.OFFLINE, "stopped")
        except:
            pass # Force offline if transition fails
            
        report = ShutdownReport(
            initiated_at=init_time,
            finished_at=time.time(),
            outcome=outcome
        )
        return report
        
    def get_status(self) -> dict:
        """Mengembalikan snapshot sistem penuh."""
        if self.supervisor:
            self.supervisor.lock.beat()
            self.health.evaluate(self.fsm, heartbeat_fresh=not self.supervisor.lock.is_stale())
        else:
            self.health.evaluate(self.fsm, heartbeat_fresh=False)
            
        return {
            "fsm": self.fsm.snapshot(),
            "health": self.health.snapshot()
        }
