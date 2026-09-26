from enum import Enum
import time

class MemoryState(str, Enum):
    """Siklus hidup Part VIII: ACTIVE -> SUPERSEDED -> ARCHIVED -> EXPIRED -> DELETED."""
    ACTIVE = "active"
    SUPERSEDED = "superseded"
    ARCHIVED = "archived"
    EXPIRED = "expired"
    DELETED = "deleted"

class MemoryLifecycle:
    def __init__(self):
        self.state = MemoryState.ACTIVE
        self.content = "Original Content"
        
    def transition(self, new_state: MemoryState):
        """Ubah state dengan aturan transisi."""
        # Active bisa ke mana saja selain langsung terhapus tanpa archive/expire?
        # Untuk tes, kita perbolehkan sesuai enum order.
        if new_state == MemoryState.ACTIVE and self.state != MemoryState.ACTIVE:
            raise ValueError("Tidak bisa kembali active (reinstatement butuh logic khusus)")
        self.state = new_state
        
    def forget(self) -> bool:
        """Idempotent forget: mengubah memory menjadi tombstone tanpa content."""
        if self.state == MemoryState.DELETED:
            return True # idempotency
            
        self.state = MemoryState.DELETED
        self.content = "" # tombstone
        return True
