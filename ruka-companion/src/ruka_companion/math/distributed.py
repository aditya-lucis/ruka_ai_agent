from enum import Enum
from typing import Dict, Tuple, Any

class VectorRelation(Enum):
    EQUAL = "equal"
    LESS = "less"
    GREATER = "greater"
    CONCURRENT = "concurrent"

def compare_version_vectors(vv1: Dict[str, int], vv2: Dict[str, int]) -> VectorRelation:
    """
    Membandingkan dua version vector.
    """
    keys = set(vv1.keys()).union(set(vv2.keys()))
    
    less_flag = False
    greater_flag = False
    
    for k in keys:
        v1 = vv1.get(k, 0)
        v2 = vv2.get(k, 0)
        
        if v1 < v2:
            less_flag = True
        elif v1 > v2:
            greater_flag = True
            
    if less_flag and greater_flag:
        return VectorRelation.CONCURRENT
    elif less_flag:
        return VectorRelation.LESS
    elif greater_flag:
        return VectorRelation.GREATER
    else:
        return VectorRelation.EQUAL

def merge_version_vectors(vv1: Dict[str, int], vv2: Dict[str, int]) -> Dict[str, int]:
    """Menggabungkan dua version vector dengan mengambil max masing-masing node."""
    keys = set(vv1.keys()).union(set(vv2.keys()))
    return {k: max(vv1.get(k, 0), vv2.get(k, 0)) for k in keys}

def resolve_lww(ts1: float, node1: str, ts2: float, node2: str) -> str:
    """
    Last-Writer-Wins tiebreaker.
    Mengembalikan 'node1' atau 'node2'.
    """
    if ts1 > ts2:
        return node1
    elif ts2 > ts1:
        return node2
    else:
        # Jika waktu persis sama, gunakan determinisme leksikal ID
        return node1 if node1 > node2 else node2


class IdempotencyCache:
    """Anti-eksekusi-ganda: key → hasil tersimpan; TTL opsional.
    Dipakai link (pesan replay) dan task queue (task_id double-delivery).
    Ttl_max 0 = tanpa kedaluwarsa. Simpan digest hasil, bukan hasil besar.
    """

    def __init__(self, max_entries: int = 4096, ttl_ms: int = 0):
        if max_entries <= 0:
            raise ValueError("max_entries > 0")
        self._max = max_entries
        self._ttl = ttl_ms
        self._seen: dict[str, int] = {}  # key → time_ms terlihat
        self._results: dict[str, object] = {}

    def seen(self, key: str, now_ms: int) -> bool:
        """True bila key pernah diproses dan masih dalam TTL."""
        if self._ttl > 0:
            self._evict(now_ms)
        return key in self._seen

    def record(self, key: str, now_ms: int, result: object = None) -> None:
        if len(self._seen) >= self._max and key not in self._seen:
            oldest = min(self._seen, key=self._seen.get)  # FIFO kasar
            self._seen.pop(oldest, None)
            self._results.pop(oldest, None)
        self._seen[key] = now_ms
        self._results[key] = result

    def result(self, key: str) -> object:
        return self._results.get(key)

    def _evict(self, now_ms: int) -> None:
        expired = [k for k, t in self._seen.items() if now_ms - t > self._ttl]
        for k in expired:
            self._seen.pop(k, None)
            self._results.pop(k, None)
