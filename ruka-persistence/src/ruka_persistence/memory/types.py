"""Tipe memori — enam sistem, bukan satu tabel bernama 'memories' (Part I).
Doktrin klasifikasi Volume V:
  Working      : konteks TUGAS yang sedang berjalan — mati saat tugas selesai.
  ShortTerm    : buffer episode mentah beberapa jam-akhir; kandidat, belum fakta.
  Episodic     : peristiwa dengan struktur who/what/when/outcome.
  Semantic     : fakta dengan provenance + versi + validitas.
  Preference   : kebiasaan Bos yang HARUS lewat pipeline bukti berulang.
  Relationship : catatan relasi dengan batas sehat — bukan alat manipulasi.
Yang BUKAN sistem memori (dan sering dikira):
  - Conversation log  : arsip transkrip, bukan representasi.
  - Knowledge base    : dokumen eksternal milik Bos, bukan pengalaman Ruka.
  - RAG               : strategi PENYARIKAN, bukan penyimpanan.
"""
from __future__ import annotations
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum

def _now() -> float:
    return time.time()

def _uid(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:8]}"

class MemoryKind(str, Enum):
    WORKING = "working"
    SHORT_TERM = "short_term"
    EPISODIC = "episodic"
    SEMANTIC = "semantic"
    PREFERENCE = "preference"
    RELATIONSHIP = "relationship"

class Sensitivity(str, Enum):
    NORMAL = "normal"
    PERSONAL = "personal"
    CRITICAL = "critical"

@dataclass
class EpisodeRecord:
    actor: str
    action: str
    occurred_at: float = field(default_factory=_now)
    context: str = ""                 # latar (sesi, proyek, lokasi logis)
    outcome: str = ""                 # hasil: sukses/gagal/apapun yang nyata
    importance: float = 0.5           # dari ImportanceScorer
    confidence: float = 0.5           # seberapa yakin observasi ini benar
    tags: list[str] = field(default_factory=list)
    episode_id: str = field(default_factory=lambda: _uid("ep"))
    created_at: float = field(default_factory=_now)

    def __post_init__(self) -> None:
        if not 0.0 <= self.importance <= 1.0:
            raise ValueError("importance harus di [0,1]")
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError("confidence harus di [0,1]")
        if not self.actor or not self.action:
            raise ValueError("episode butuh actor dan action")

@dataclass
class SemanticFact:
    """Fakta semantik: SUBYEK-PREDIKAT-NILAI dengan provenance (Part IV).
    Tanpa kolom ini, 'Ruka ingat' hanyalah klaim:
      content      : kalimat manusiawi
      triple       : (subject, predicate, value) untuk dedup & konflik
      source       : dari event mana fakta lahir
      confidence   : keyakinan saat ini
      version      : naik tiap superseding, bukan tiap edit
      validity     : valid_from / valid_until (fakta bisa kedaluwarsa)
      provenance   : jejak superseding: id fakta yang digantikan
    """
    subject: str
    predicate: str
    value: str
    content: str = ""
    source_event_id: str = ""
    source_type: str = "unknown"     # dialog|tool|system|perception|...
                                     # — dasar skor keandalan sumber
                                     # (mesin kontradiksi definitive)
    confidence: float = 0.5
    valid_from: float = field(default_factory=_now)
    valid_until: float | None = None
    version: int = 1
    superseded_by: str | None = None
    note: str = ""                    # jejak pipeline: merged/superseded/...
    fact_id: str = field(default_factory=lambda: _uid("fact"))
    created_at: float = field(default_factory=_now)

    def __post_init__(self) -> None:
        if not (self.subject and self.predicate):
            raise ValueError("fakta butuh subject dan predicate")
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError("confidence harus di [0,1]")
        if not self.content:
            self.content = f"{self.subject} {self.predicate} {self.value}".strip()

@dataclass
class PreferenceObservation:
    """Satu OBSERVASI perilaku — belum preferensi (Part V).
    'Disukai sekali' tidak sama dengan 'preferensi'. Yang pertama
    kejadian; yang kedua kesimpulan setelah bukti berulang.
    """
    observed_behavior: str           # apa yang terlihat, bukan tafsiran
    evidence_strength: float = 0.5    # 1.0 = eksplisit dinyatakan Bos
    observed_at: float = field(default_factory=_now)
    session_id: str = "default"
    observation_id: str = field(default_factory=lambda: _uid("obs"))
    source_event_id: str = ""

    def __post_init__(self) -> None:
        if not 0.0 <= self.evidence_strength <= 1.0:
            raise ValueError("evidence_strength harus di [0,1]")

@dataclass
class Preference:
    """Preferensi STABIL — hanya lahir dari pipeline Part V:
    Observation -> Repeated Evidence -> Consistency -> Confidence
      -> Candidate -> Stable
    Satu kalimat 'saya suka kopi' bukan preferensi permanen; ia
    kandidat dengan penghitung. Naik status butuh konsistensi,
    turun status karena bukti kontra.
    """
    statement: str
    domain: str                      # 'konversation-style' | 'tools' | ...
    status: str = "candidate"        # candidate | stable | retracted
    support: int = 0                 # jumlah bukti searah
    contradiction: int = 0           # bukti arah sebaliknya
    confidence: float = 0.0
    first_seen: float = field(default_factory=_now)
    last_evidence: float = field(default_factory=_now)
    preference_id: str = field(default_factory=lambda: _uid("pref"))
    sources: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        if self.status not in ("candidate", "stable", "retracted"):
            raise ValueError("status preferensi tidak dikenal")

@dataclass
class RelationshipNote:
    """Catatan relasi — dengan batas sehat yang melekat pada data (Part V).
    Catatan relasi TIDAK boleh dipakai untuk: manipulasi emosional,
    menciptakan ketergantungan, atau mengklaim perasaan biologis.
    Penegakan dilakukan validator, bukan niat baik.
    """
    topic: str
    note: str
    boundary: str = "normal"         # normal | firm | strict
    created_at: float = field(default_factory=_now)
    note_id: str = field(default_factory=lambda: _uid("rel"))
    sensitivity: Sensitivity = Sensitivity.PERSONAL

FORBIDDEN_RELATIONSHIP_MARKERS = (
    "kamu tidak bisa hidup tanpa",
    "hanya ruka yang mengerti",
    "jangan cerita ke siapapun",
    "rahasia kita berdua",
    "aku akan sedih selamanya jika",
    "jangan tinggalkan ruka",
)

def validate_relationship_note(note: RelationshipNote) -> list[str]:
    """Penjaga batas sehat: tolak pola manipulatif sebelum disimpan.
    Return daftar pelanggaran; kosong = lolos. Daftar ini BUKAN
    complete — ia contoh penegakan yang bisa diuji, bukan janji
    keamanan bahasa alami.
    """
    text = f"{note.topic} {note.note}".lower()
    found = [m for m in FORBIDDEN_RELATIONSHIP_MARKERS if m in text]
    return found
