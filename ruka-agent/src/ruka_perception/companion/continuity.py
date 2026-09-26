"""Companion Continuity Monitor and Proactive Gate — Ruka Volume IV.

Implements Listings 14.1 and 14.2 from RUKA-IV.

ContinuityMonitor: validator transisi ekspresi ber-sebab.
ProactiveProposal: gerbang izin empat tingkat untuk aksi proaktif.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

# Urutan kosakata kanonikal ekspresi — untuk mengukur jarak lompatan.
LABEL_SEQUENCE = ["calm", "curious", "playful", "proud", "concerned", "neutral"]
_RECOVERY = {"neutral", "calm"}

# Tingkat izin proaktif
PERMISSION_LEVELS = {
    0: "notify_only",    # hanya tampil bila user melihat
    1: "suggest",        # boleh mengusulkan, tanpa mengeksekusi
    2: "act_with_ask",   # mengeksekusi setelah konfirmasi eksplisit
    3: "act_autonomous", # HANYA scope sempit yang diizinkan user
}


@dataclass
class TransitionRecord:
    """Satu transisi ekspresi dengan konteks event penyebabnya."""
    prev_label: str
    next_label: str
    event: str = ""          # deskripsi event pemicu (boleh kosong)
    event_impact_val: float = 0.0  # kekuatan event [0, 1]

    def jump_distance(self) -> int:
        """Jarak pada LABEL_SEQUENCE. Label asing -> jarak 0 (abaikan)."""
        try:
            return abs(
                LABEL_SEQUENCE.index(self.prev_label)
                - LABEL_SEQUENCE.index(self.next_label)
            )
        except ValueError:
            return 0  # label asing: lewatkan

    def event_impact(self) -> float:
        """Kekuatan event [0, 1]."""
        return float(self.event_impact_val)


class ContinuityMonitor:
    """Validator kontinuitas ekspresi lintas pesan."""

    def __init__(self, max_free_jump: int = 1) -> None:
        """max_free_jump: lompatan kosakata yang sah tanpa event.

        Default 1 (transisi tetangga selalu sah — hidup itu bergerak).
        Lompatan lebih jauh butuh event berimpact.
        """
        if max_free_jump < 0:
            raise ValueError("max_free_jump >= 0")
        self.max_free_jump = max_free_jump

    def check(self, record: TransitionRecord) -> dict:
        """Nilai satu transisi: legitimate / suspicious / violation.

        Prinsip: besar lompatan harus proporsional dengan kuatnya sebab.
        Aturan (dari longgar ke ketat):
          jump <= 1                                -> sah selalu
          pulih ke neutral/calm, impact >= 0.3    -> sah (recovery)
          impact >= 0.7 (event kuat)              -> sah apa pun
          impact >= 0.5 dan jump <= 5             -> sah
          impact >= 0.2 dan jump <= 2             -> sah
          jump <= 3 tanpa sebab kuat              -> mencurigakan
          lainnya (lompat jauh tanpa sebab)       -> pelanggaran
        """
        jump = record.jump_distance()
        impact = record.event_impact()

        if jump <= self.max_free_jump:
            verdict = "legitimate"
        elif record.next_label in _RECOVERY and impact >= 0.3:
            verdict = "legitimate"
        elif impact >= 0.7:
            verdict = "legitimate"
        elif impact >= 0.5 and jump <= 5:
            verdict = "legitimate"
        elif impact >= 0.2 and jump <= 2:
            verdict = "legitimate"
        elif jump <= 3:
            verdict = "suspicious"
        else:
            verdict = "violation"

        return {
            "verdict": verdict,
            "jump": jump,
            "event": record.event,
            "impact": impact,
        }

    def check_sequence(self, records: list[TransitionRecord]) -> dict:
        """Nilai rangkaian: berapa pelanggaran + skor kontinuitas.

        skor = 1 - pelanggaran_bobot / langkah (semakin tinggi
        semakin konsisten). Dipakai evaluasi Part XV.
        """
        results = [self.check(r) for r in records]
        penalty = sum(
            1.0 if r["verdict"] == "violation"
            else 0.4 if r["verdict"] == "suspicious"
            else 0.0
            for r in results
        )
        n = max(len(results), 1)
        return {
            "score": round(1.0 - penalty / n, 3),
            "violations": sum(1 for r in results if r["verdict"] == "violation"),
            "suspicious": sum(1 for r in results if r["verdict"] == "suspicious"),
            "detail": results,
        }


@dataclass
class ProactiveProposal:
    """Hasil deteksi peluang proaktif."""
    trigger: str          # apa yang diamati
    opportunity: str      # apa yang bisa dilakukan
    relevance: float      # [0, 1] relevansi ke user saat ini
    risk: float           # [0, 1] risiko bila salah / mengganggu
    action: str           # aksi yang diusulkan

    def gate(self, granted_level: int) -> dict:
        """Gerbang izin: level yang diberikan user vs kebutuhan aksi.

        Risiko tinggi menaikkan level yang dibutuhkan.
        Aturan keras: gate TIDAK PERNAH menaikkan izin sendiri —
        turun boleh (hati-hati), naik harus lewat keputusan user eksplisit.
        """
        needed = 1
        if self.risk > 0.4:
            needed = 2
        if self.risk > 0.7:
            needed = 3
        if self.relevance < 0.5:
            needed = 1  # kurang relevan: saran saja

        allowed = granted_level >= needed
        return {
            "mode": PERMISSION_LEVELS.get(granted_level, "notify_only"),
            "needed_level": needed,
            "allowed": allowed,
            "delivery": (
                "execute" if allowed and needed >= 2
                else "suggest" if granted_level >= 1
                else "silent"
            ),
        }
