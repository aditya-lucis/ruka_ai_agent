# -*- coding: utf-8 -*-
"""RUKA Skills System — Models and Data Structures.

Mendefinisikan entitas Skill, atribut metadata YAML,
serta struktur hasil eksekusi SkillExecutionResult.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable


@dataclass
class Skill:
    """Representasi sebuah Skill dalam ekosistem Ruka."""
    name: str
    version: str
    description: str
    author: str = "Ruka Core Team"
    license: str = "MIT"
    tags: list[str] = field(default_factory=list)
    risk_level: str = "medium"                           # low | medium | high | critical
    requires_confirmation: bool = False
    permissions: list[str] = field(default_factory=list) # e.g. ["filesystem:read"]
    entry_point: str | None = None
    timeout_seconds: float = 30.0
    instructions_md: str = ""
    folder_path: Path | None = None
    handler: Callable[..., Any] | None = None

    def __repr__(self) -> str:
        return f"Skill(name={self.name!r}, version={self.version!r}, risk={self.risk_level!r})"


@dataclass
class SkillExecutionResult:
    """Hasil eksekusi skill yang dinormalisasi."""
    success: bool
    data: Any = None
    error: str | None = None
    duration_seconds: float = 0.0
    skill_name: str = ""
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        return {
            "success": self.success,
            "skill_name": self.skill_name,
            "data": self.data,
            "error": self.error,
            "duration_seconds": round(self.duration_seconds, 4),
            "timestamp": self.timestamp,
        }
