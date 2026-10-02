# -*- coding: utf-8 -*-
"""RUKA Skills System — Skill Registry.

Pusat pendaftaran, pencarian, dan pengelolaan kemampuan (Skills)
yang tersedia untuk dipanggil oleh Cognitive Core atau Gateway.
"""
from __future__ import annotations

import logging
import threading
from typing import Sequence

from src.gateway.skills.models import Skill

log = logging.getLogger("ruka.gateway.skills.registry")


class SkillRegistry:
    """Registry penyimpan seluruh skill terdaftar secara thread-safe."""

    def __init__(self) -> None:
        self._skills: dict[str, Skill] = {}
        self._lock = threading.RLock()

    def register(self, skill: Skill) -> None:
        """Mendaftarkan skill baru ke dalam registry."""
        with self._lock:
            self._skills[skill.name] = skill
            log.info("Skill '%s' (v%s) berhasil didaftarkan.", skill.name, skill.version)

    def get(self, name: str) -> Skill | None:
        """Mengambil skill berdasarkan nama uniknya."""
        with self._lock:
            return self._skills.get(name)

    def unregister(self, name: str) -> bool:
        """Menghapus skill dari registry."""
        with self._lock:
            if name in self._skills:
                del self._skills[name]
                return True
            return False

    def list(self, tag: str | None = None) -> list[Skill]:
        """Mengembalikan daftar skill, dapat difilter berdasarkan tag."""
        with self._lock:
            if tag is None:
                return list(self._skills.values())
            return [s for s in self._skills.values() if tag in s.tags]

    def search(self, query: str) -> list[Skill]:
        """Mencari skill berdasarkan kesesuaian nama, deskripsi, atau tags."""
        q = query.lower().strip()
        with self._lock:
            matches: list[Skill] = []
            for s in self._skills.values():
                if (
                    q in s.name.lower()
                    or q in s.description.lower()
                    or any(q in t.lower() for t in s.tags)
                ):
                    matches.append(s)
            return matches

    def to_tool_definitions(self) -> list[dict[str, str]]:
        """Mengkonversi metadata skills menjadi format ringkas untuk prompt System 2 LLM."""
        with self._lock:
            return [
                {
                    "name": s.name,
                    "version": s.version,
                    "description": s.description.strip(),
                    "risk_level": s.risk_level,
                    "tags": ", ".join(s.tags),
                }
                for s in self._skills.values()
            ]
