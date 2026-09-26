"""Multimodal Memory — kebijakan retensi dan gerbang consent.

Implements Listings 13.2 and 13.3 from RUKA-IV.

PERSEPSI BUKAN MEMORI:
  MELIHAT ≠ MENGINGAT : bytes hidup di buffer satu giliran, masuk prompt, lalu dibuang.
  MENDENGAR ≠ MENYIMPAN: transkrip boleh masuk memori, rekaman mentah tidak (tanpa consent).
  MEMPROSES ≠ JANGKA PANJANG: kandidat harus LULUS gerbang nilai sebelum menjadi ingatan.
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class Modality(str, Enum):
    TEXT = "text"
    IMAGE = "image"
    AUDIO = "audio"
    INTERACTION_EVENT = "interaction_event"
    UNKNOWN = "unknown"


# Kebijakan retensi per kelas: (TTL detik, kuota item)
RETENTION_POLICY: dict[str, tuple[float, int]] = {
    "conversation":      (7 * 86400,   500),    # 7 hari
    "semantic":          (365 * 86400, 200),    # 365 hari (ingatan penting)
    "visual_episode":    (30 * 86400,  100),    # 30 hari
    "audio_episode":     (30 * 86400,  100),    # 30 hari
    "interaction_event": (90 * 86400,  300),    # 90 hari
}


@dataclass
class MemoryCandidate:
    """Kandidat memori yang ditawarkan ke MultimodalMemory.

    Bytes mentah TIDAK disimpan tanpa consent eksplisit (RAW GATE).
    """
    modality: Modality
    summary: str
    importance: float                               # [0, 1]
    sensitivity: str = "low"                       # low / medium / high
    keep_raw: bool = False                         # minta simpan bytes
    embedding: list[float] | None = None           # opsional, untuk retrieval
    metadata: dict[str, Any] = field(default_factory=dict)
    candidate_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    created_at: float = field(default_factory=time.time)


def memory_class(modality: Modality, importance: float) -> str:
    """Klasifikasi kandidat ke kelas retensi.

    Interaksi penting (importance >= 0.8) naik kelas menjadi semantic
    — memori jangka panjang — karena layak bertahan setahun.
    """
    if importance >= 0.8:
        return "semantic"
    return {
        Modality.TEXT: "conversation",
        Modality.IMAGE: "visual_episode",
        Modality.AUDIO: "audio_episode",
        Modality.INTERACTION_EVENT: "interaction_event",
        Modality.UNKNOWN: "conversation",
    }[modality]


class AdmissionPolicy:
    """Gerbang evaluation: kandidat layak disimpan atau tidak?

    Rule-based BY DESIGN (Vol III Part VI: rule-based dulu, neural
    hanya bila menang jujur). Skor = bobot importance + keunikan
    ringkasan + tanda eksplisit user ('ingat ini').
    """

    def __init__(self, threshold: float = 0.45) -> None:
        if not (0 <= threshold <= 1):
            raise ValueError("threshold di [0,1]")
        self.threshold = threshold

    def evaluate(self, cand: MemoryCandidate) -> tuple[bool, float]:
        """Return (admitted, score)."""
        explicit = 1.0 if cand.metadata.get("user_flagged") else 0.0
        uniqueness = 1.0 if cand.metadata.get("novel") else 0.3
        score = 0.5 * cand.importance + 0.25 * uniqueness + 0.25 * explicit
        admitted = score >= self.threshold or explicit > 0
        return admitted, float(score)


class MultimodalMemory:
    """Penyimpanan in-process + kebijakan.

    Bukan database — kelas ini KONTRAK dan mesin kebijakan;
    persistensi nyata (SQLite dsb.) tugas infrastruktur.
    """

    def __init__(
        self,
        policy: AdmissionPolicy | None = None,
        now: Any = None,
    ) -> None:
        self.policy = policy or AdmissionPolicy()
        self._now = now or time.time
        self.items: dict[str, dict] = {}
        self.rejected: list[dict] = []

    def offer(self, cand: MemoryCandidate) -> tuple[bool, str]:
        """Tawarkan kandidat. Return (disimpan?, memory_id).

        RAW GATE: tanpa consent, tolak menyimpan bytes.
        """
        if cand.keep_raw and not cand.metadata.get("user_consent"):
            self.rejected.append(
                {"reason": "raw_without_consent", "summary": cand.summary[:80]}
            )
            return False, ""
        admitted, score = self.policy.evaluate(cand)
        if not admitted:
            self.rejected.append(
                {
                    "reason": "below_threshold",
                    "score": round(score, 3),
                    "summary": cand.summary[:80],
                }
            )
            return False, ""
        mclass = memory_class(cand.modality, cand.importance)
        ttl, _quota = RETENTION_POLICY[mclass]
        mid = cand.candidate_id
        self.items[mid] = {
            "id": mid,
            "class": mclass,
            "modality": cand.modality.value,
            "summary": cand.summary,
            "importance": cand.importance,
            "sensitivity": cand.sensitivity,
            "embedding": cand.embedding,
            "metadata": cand.metadata,
            "keep_raw": bool(cand.keep_raw),
            "created_at": cand.created_at,
            "expires_at": cand.created_at + ttl,
        }
        return True, mid

    # ---------------- user control ---------------------------------

    def list_all(self) -> list[dict]:
        """Daftar memori (ringkasan — untuk panel kontrol user)."""
        return [
            {
                "id": v["id"],
                "class": v["class"],
                "modality": v["modality"],
                "summary": v["summary"][:60],
                "sensitivity": v["sensitivity"],
            }
            for v in self.items.values()
        ]

    def forget(self, memory_id: str) -> bool:
        """Hapus total. Kembalikan False bila tidak ada (idempoten)."""
        return self.items.pop(memory_id, None) is not None

    def sweep_expired(self) -> int:
        """Buang yang lewat TTL. Return jumlah yang dibuang."""
        now = self._now()
        expired = [k for k, v in self.items.items() if v["expires_at"] <= now]
        for k in expired:
            del self.items[k]
        return len(expired)
