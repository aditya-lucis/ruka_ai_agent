# -*- coding: utf-8 -*-
"""Escalation Matrix (18 cells) & 4-Part Failure Reporter (FR-HE-13, FR-HE-15).

Matriks Eskalasi 18 sel:
- 3 tingkat risiko (GREEN, YELLOW, RED) x 6 tingkat otonomi (0 sampai 5)
- GREEN berjalan otomatis pada otonomi >= 1
- YELLOW bertanya pada level 0 sampai 3, otomatis di level 4-5
- RED selalu meminta konfirmasi tanpa kompromi di semua level
- Penolakan pengguna adalah keluaran sah, bukan galat

Laporan Kegagalan 4 Bagian:
1. Apa yang dicoba
2. Di mana macet beserta bukti
3. Tepat 3 opsi pemulihan
4. Permintaan keputusan
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any
from src.heart.blood import BloodPermission


class EscalationDecision(str, Enum):
    EXECUTE_AUTO = "execute_auto"
    ASK_USER = "ask_user"


class EscalationMatrix:
    def __init__(self, default_autonomy_level: int = 2) -> None:
        self.autonomy_level = max(0, min(5, default_autonomy_level))

    def evaluate(self, permission: BloodPermission) -> EscalationDecision:
        """Mengevaluasi apakah alat dapat dieksekusi otomatis atau harus bertanya."""
        # RED: SELALU bertanya di level berapa pun
        if permission == BloodPermission.RED:
            return EscalationDecision.ASK_USER

        # Level 0 (Pengamat Murni): semuanya bertanya
        if self.autonomy_level == 0:
            return EscalationDecision.ASK_USER

        # GREEN: otomatis di level 1 sampai 5
        if permission == BloodPermission.GREEN:
            return EscalationDecision.EXECUTE_AUTO

        # YELLOW: bertanya di level 1-3, otomatis di level 4-5
        if permission == BloodPermission.YELLOW:
            if self.autonomy_level >= 4:
                return EscalationDecision.EXECUTE_AUTO
            return EscalationDecision.ASK_USER

        return EscalationDecision.ASK_USER


@dataclass(frozen=True)
class StructuredFailureReport:
    """Laporan kegagalan 4 bagian terstruktur (FR-HE-15)."""
    attempted: str
    stuck_point_with_evidence: str
    recovery_options: tuple[str, str, str]  # Tepat 3 opsi
    decision_request: str

    def to_markdown(self) -> str:
        return (
            f"### Laporan Hambatan Tugas (Marquis Status)\n\n"
            f"**1. Apa yang Dicoba:**\n{self.attempted}\n\n"
            f"**2. Titik Macet & Bukti:**\n{self.stuck_point_with_evidence}\n\n"
            f"**3. Tiga Opsi Pemulihan:**\n"
            f"- **Opsi A:** {self.recovery_options[0]}\n"
            f"- **Opsi B:** {self.recovery_options[1]}\n"
            f"- **Opsi C:** {self.recovery_options[2]}\n\n"
            f"**4. Keputusan Anda, My Lord:**\n{self.decision_request}"
        )
