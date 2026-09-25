"""Memory revision engine — konflik, resolusi, supersedes.
Kebijakan inti: TIDAK ADA penghapusan data karena revisi. Record kalah
menjadi arsip (supersedes_id diisi) dan berhenti direcall. Hapus
permanent hanya lewat jalur user (PART 10).
"""
from __future__ import annotations
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from src.memory.models import MemoryKind, MemoryRecord

PROVENANCE_WEIGHT = {
    "conversation": 1.0,
    "document": 0.6,
    "tool": 0.5,
    "system": 0.3,
}

@dataclass(frozen=True)
class ConflictVerdict:
    winner: MemoryRecord
    loser: MemoryRecord
    score_winner: float
    score_loser: float
    reason: str

PREFERENCE_OVERRIDES = re.compile(
    r"\b(sekarang|dari sekarang|tak lagi|tidak lagi|ganti|switch|"
    r"lebih suka|prefer)\b", re.IGNORECASE
)

def looks_like_override(text: str) -> bool:
    """Sinyal leksikal bahwa kalimat ini MENIMPA preferensi lama.
    Sinyal kuat -> bypass pencocokan topik (jaga recall tinggi).
    False positif aman: resolusi tetap menilai bukti."""
    return bool(PREFERENCE_OVERRIDES.search(text))

def same_topic(a: MemoryRecord, b: MemoryRecord) -> bool:
    """Topik kasar: token konten yang tumpang tindih >= 1 kata
    signifikan (bukan stopwords) — sederhana, bisa diganti embedding
    similarity (lihat PART 20: kapan upgrade sah?)."""
    STOP = {"saya", "lebih", "suka", "yang", "dan", "dengan",
            "untuk", "pendekatan", "pakai", "memakai", "sekarang", "tak"}
    wa = {w for w in re.findall(r"\w{4,}", a.content.lower()) if w not in STOP}
    wb = {w for w in re.findall(r"\w{4,}", b.content.lower()) if w not in STOP}
    if bool(wa & wb):
        return True
    ARCH_TERMS = {"monolith", "microservice", "microservices", "modular"}
    if bool(wa & ARCH_TERMS) and bool(wb & ARCH_TERMS):
        return True
    return False

def _score(r: MemoryRecord, now: datetime) -> float:
    # Mengatasi perbandingan naive vs aware datetime jika created_at tidak memiliki timezone
    created = r.created_at
    if created.tzinfo is None:
        created = created.replace(tzinfo=timezone.utc)
    if now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)
        
    age_days = max(0.0, (now - created).total_seconds() / 86400)
    recency = 1.0 / (1.0 + age_days / 30.0)          # half-life 30 hari
    pw = PROVENANCE_WEIGHT.get(r.provenance.source_type if r.provenance else "system", 0.3)
    return 0.5 * recency + 0.3 * r.confidence + 0.2 * pw

class MemoryRevisionStrategy:
    """Deteksi + resolusi + penandaan supersedes."""
    def __init__(self, store) -> None:
        self._store = store                   # governor's store (PART 8)

    def revise_preference(self, new: MemoryRecord,
                          now: datetime | None = None) -> ConflictVerdict | None:
        """Kandidat lawan: preference aktif se-topik yang BUKAN
        pendahulu eksplisitnya. Kembalikan None jika tak ada konflik."""
        now = now or datetime.now(timezone.utc)
        candidates = [r for r in self._store.query_memories(
                          kinds=[MemoryKind.PREFERENCE.value], active_only=True)
                      if r.supersedes_id is None and getattr(r, "id", None) != getattr(new, "id", None)]
        opponents = [r for r in candidates
                     if same_topic(r, new)
                     or (looks_like_override(new.content) and same_topic(r, new))]
        if not opponents:
            return None
        scored = sorted(((_score(r, now), r) for r in opponents),
                        key=lambda pair: -pair[0])
        loser_score, loser = scored[0]
        winner_score = _score(new, now)
        if winner_score <= loser_score:
            # pernyataan baru kalah? tetap simpan, tapi jangan timpa —
            # konflik dikerek ke antrian tinjauan (trace), bukan senyap.
            return ConflictVerdict(winner=loser, loser=new,
                                   score_winner=loser_score,
                                   score_loser=winner_score,
                                   reason="pernyataan baru kalah bukti — ditinjau")
        return ConflictVerdict(winner=new, loser=loser,
                               score_winner=winner_score,
                               score_loser=loser_score,
                               reason="recency+confidence+provenance")

    def apply(self, verdict: ConflictVerdict) -> None:
        """Tandai loser sebagai arsip — TANPA menghapus."""
        self._store.mark_superseded(loser_id=verdict.loser.id,
                                    winner_id=verdict.winner.id,
                                    reason=verdict.reason)

def consolidation_sweep(store, now: datetime | None = None) -> dict:
    """Fold percakapan panjang jadi summary + tandai kedaluwarsa.
    Berjalan berkala (bukan per giliran) — cheap, offline."""
    now = now or datetime.now(timezone.utc)
    stats = {"folded": 0, "expired_archived": 0}
    for r in store.query_memories(kinds=[MemoryKind.CONVERSATION.value],
                                  active_only=True):
        if r.is_expired(now):
            if hasattr(store, "archive"):
                store.archive(r.id)
            stats["expired_archived"] += 1
    # fold nyata: distill via LLM dilakukan caller (budgeted, PART 13)
    return stats
