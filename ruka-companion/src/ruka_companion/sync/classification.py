"""RUKA VI: Memory Synchronization — 6-Level Classification & Boundary Gates.
Strictly follows RUKA-VI Chapter XX (baris 55-110).
"""

from __future__ import annotations

from enum import IntEnum
from typing import Any


class SyncClass(IntEnum):
    """Enam kelas sinkronisasi memori (Part XX)."""

    PUBLIC = 1
    PERSONAL = 2
    PRIVATE = 3
    SENSITIVE = 4
    LOCAL_ONLY = 5
    NEVER_SYNC = 6


NEVER_SYNC_KEYS: frozenset[str] = frozenset(
    {
        "secret",
        "token",
        "password",
        "api_key",
        "verify_token",
        "private_key",
        "credential",
        "biometric_raw",
        "raw_biometrics",
        "embedding_raw",
        "face_embedding",
        "voice_embedding",
    }
)


LEGACY_SENSITIVITY_MAP: dict[str, SyncClass] = {
    "NORMAL": SyncClass.PRIVATE,
    "PERSONAL": SyncClass.SENSITIVE,
    "SENSITIVE": SyncClass.LOCAL_ONLY,
}

MEMORY_SYSTEM_DEFAULT: dict[str, SyncClass] = {
    "facts": SyncClass.PRIVATE,
    "preferences": SyncClass.PERSONAL,
    "notes": SyncClass.PRIVATE,
    "working_memory": SyncClass.LOCAL_ONLY,
    "vault": SyncClass.NEVER_SYNC,
}


class SyncClassifier:
    """Klasifikasi + penegakan batas sinkronisasi."""

    def __init__(self, defaults: dict[str, SyncClass] | None = None) -> None:
        self.defaults = dict(defaults or MEMORY_SYSTEM_DEFAULT)

    def classify(
        self,
        memory_system: str,
        sensitivity: str | None = None,
        payload_keys: set[str] | None = None,
    ) -> SyncClass:
        # 1. mapping warisan eksplisit
        if (
            sensitivity is not None
            and sensitivity.upper() in LEGACY_SENSITIVITY_MAP
        ):
            base = LEGACY_SENSITIVITY_MAP[sensitivity.upper()]
        else:
            base = self.defaults.get(memory_system, SyncClass.LOCAL_ONLY)

        # 2. kunci haram → NEVER_SYNC langsung (paling kuat)
        if payload_keys and (payload_keys & NEVER_SYNC_KEYS):
            return SyncClass.NEVER_SYNC
        return base

    def can_sync(self, cls_: SyncClass, direction: str = "to_cloud") -> bool:
        """LOCAL_ONLY & NEVER_SYNC tidak pernah keluar; SENSITIVE hanya
        cloud (bukan plugin pihak ketiga)."""
        if cls_ >= SyncClass.LOCAL_ONLY:
            return False
        if direction == "to_plugin":
            return cls_ <= SyncClass.PUBLIC
        return True

    def report(self, cls_: SyncClass) -> dict[str, Any]:
        return {
            "class": cls_.name,
            "to_cloud": self.can_sync(cls_, "to_cloud"),
            "to_plugin": self.can_sync(cls_, "to_plugin"),
            "note": (
                "LOCAL_ONLY/NEVER_SYNC tetap di perangkat — privacy by construction"
            ),
        }
