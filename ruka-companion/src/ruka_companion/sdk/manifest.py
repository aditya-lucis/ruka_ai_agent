"""RUKA VI: Plugin Manifest — Declarative Contract and Risk Validation.
Strictly follows RUKA-VI Chapter XXI (baris 38-110).
"""

from __future__ import annotations

import re
from typing import Any
from pydantic import BaseModel, Field, field_validator


PLUGIN_ID_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
SEMVER_RE = re.compile(r"^\d+\.\d+\.\d+$")

PLUGIN_PERMISSIONS: frozenset[str] = frozenset(
    {
        "memory.read",
        "memory.write",
        "event.subscribe",
        "presence.read",
        "tasks.read",
    }
)

RISKY_PERMISSIONS: frozenset[str] = frozenset(
    {
        "terminal.execute",
        "network.outbound",
        "filesystem.raw",
        "identity.admin",
    }
)


class PluginManifest(BaseModel):
    """Manifest plugin Pydantic — izin HARUS subset dari daftar yang dikenal sistem."""

    plugin_id: str
    name: str = Field(min_length=1, max_length=80)
    version: str
    description: str = Field(min_length=10, max_length=400)
    ruka_compat: str  # semver range sederhana "0.1.x"
    permissions: list[str] = Field(default_factory=list)
    entrypoint: str = Field(min_length=3, max_length=200)
    dependencies: list[str] = Field(default_factory=list)
    author: str = ""
    risk_notes: str = ""
    must_declare_risk: bool = False

    @field_validator("plugin_id")
    @classmethod
    def _id(cls, v: str) -> str:
        if not PLUGIN_ID_RE.match(v):
            raise ValueError(f"plugin_id '{v}' harus slug kecil")
        return v

    @field_validator("version", "ruka_compat")
    @classmethod
    def _semver(cls, v: str) -> str:
        if not SEMVER_RE.match(v) and "x" not in v:
            raise ValueError(f"'{v}' bukan semver/semver-range")
        return v

    @field_validator("permissions")
    @classmethod
    def _perms(cls, v: list[str]) -> list[str]:
        unknown = set(v) - PLUGIN_PERMISSIONS - RISKY_PERMISSIONS
        if unknown:
            raise ValueError(f"izin tak dikenal (default deny): {sorted(unknown)}")
        if len(set(v)) != len(v):
            raise ValueError("izin duplikat")
        return v

    def validate_risk(self) -> None:
        risky = set(self.permissions) & RISKY_PERMISSIONS
        if risky and not self.must_declare_risk:
            raise ValueError(
                f"izin berisiko {sorted(risky)} menuntut must_declare_risk=True"
            )
        if self.must_declare_risk and not self.risk_notes:
            raise ValueError("must_declare_risk tanpa risk_notes — tolak")

    def as_dict(self) -> dict[str, Any]:
        return self.model_dump()
