"""RUKA VI: Plugin Registry — Lifecycle, Dependency DAG, and Permission Enforcement.
Strictly follows RUKA-VI Chapter XXI (baris 55-215).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable

from ruka_companion.math.discrete import Digraph, topological_order
from .manifest import PluginManifest, RISKY_PERMISSIONS


class PluginState(str, Enum):
    """Sembilan status siklus hidup plugin."""

    DISCOVERED = "DISCOVERED"
    VALIDATED = "VALIDATED"
    STAGED = "STAGED"
    INSTALLED = "INSTALLED"
    ENABLED = "ENABLED"
    DISABLED = "DISABLED"
    REMOVED = "REMOVED"
    REJECTED = "REJECTED"
    FAILED_INSTALL = "FAILED_INSTALL"


_PLUGIN_TRANSITIONS: frozenset[tuple[str, str]] = frozenset(
    {
        (PluginState.DISCOVERED, PluginState.VALIDATED),
        (PluginState.DISCOVERED, PluginState.REJECTED),
        (PluginState.VALIDATED, PluginState.STAGED),
        (PluginState.STAGED, PluginState.INSTALLED),
        (PluginState.STAGED, PluginState.REJECTED),
        (PluginState.STAGED, PluginState.FAILED_INSTALL),
        (PluginState.INSTALLED, PluginState.ENABLED),
        (PluginState.INSTALLED, PluginState.REMOVED),
        (PluginState.ENABLED, PluginState.DISABLED),
        (PluginState.DISABLED, PluginState.ENABLED),
        (PluginState.DISABLED, PluginState.REMOVED),
        (PluginState.REJECTED, PluginState.REMOVED),
        (PluginState.FAILED_INSTALL, PluginState.REMOVED),
    }
)


@dataclass
class PluginRecord:
    manifest: PluginManifest
    state: str = PluginState.DISCOVERED
    granted_permissions: frozenset[str] = field(default_factory=frozenset)
    rejection_reason: str = ""


class PluginRegistry:
    """Registri + lifecycle + dependency DAG + permission enforcement."""

    def __init__(self, loader: Callable[[str], Any] | None = None) -> None:
        self._plugins: dict[str, PluginRecord] = {}
        self._loader = loader  # memuat modul entrypoint (injeksi saat uji)

    # ------------------------------------------------------------ discovery
    def discover(self, manifest: PluginManifest) -> PluginRecord:
        if manifest.plugin_id in self._plugins:
            raise ValueError(f"plugin {manifest.plugin_id} sudah ada")
        rec = PluginRecord(manifest=manifest)
        self._plugins[manifest.plugin_id] = rec
        return rec

    def validate(self, plugin_id: str) -> PluginRecord:
        rec = self._get(plugin_id)
        if rec.state != PluginState.DISCOVERED:
            raise ValueError(f"validasi hanya dari DISCOVERED, dapat {rec.state}")
        try:
            rec.manifest.validate_risk()
            self._check_dependencies(plugin_id)
        except ValueError as exc:
            rec.state = PluginState.REJECTED
            rec.rejection_reason = str(exc)
            return rec
        rec.state = PluginState.VALIDATED
        return rec

    def _check_dependencies(self, plugin_id: str) -> None:
        """Dependency harus (a) terinstal ATAU (b) ikut ditemukan + DAG bebas siklus."""
        g = Digraph()
        for pid in self._plugins:
            g.add_node(pid)
        for pid, rec in self._plugins.items():
            for dep in rec.manifest.dependencies:
                if dep not in self._plugins and dep not in ("ruka-sdk",):
                    raise ValueError(f"{pid}: dependensi {dep} tidak ada")
                if dep in self._plugins:
                    g.add_edge(dep, pid)
        order = topological_order(g)
        if not order and len(self._plugins) > 0:
            raise ValueError("dependency graph ber-SIKLUS — ditolak")

    # -------------------------------------------------------------- install
    def stage(self, plugin_id: str) -> PluginRecord:
        rec = self._get(plugin_id)
        self._transition(plugin_id, PluginState.STAGED)
        return rec

    def install(
        self, plugin_id: str, owner_confirm: bool = False
    ) -> PluginRecord:
        """Instalasi — izin berisiko MENUNTUT owner_confirm (default deny)."""
        rec = self._get(plugin_id)
        if rec.state != PluginState.STAGED:
            raise ValueError(f"instalasi hanya dari STAGED, dapat {rec.state}")
        risky = set(rec.manifest.permissions) & RISKY_PERMISSIONS
        if risky and not owner_confirm:
            rec.state = PluginState.REJECTED
            rec.rejection_reason = (
                f"izin berisiko {sorted(risky)} butuh konfirmasi pemilik — "
                "instalasi DITOLAK (default deny)"
            )
            return rec
        if self._loader is not None:
            try:
                self._loader(rec.manifest.entrypoint)
            except Exception as exc:
                rec.state = PluginState.FAILED_INSTALL
                rec.rejection_reason = f"loader gagal: {exc}"
                return rec
        rec.granted_permissions = frozenset(rec.manifest.permissions)
        rec.state = PluginState.INSTALLED
        return rec

    def enable(self, plugin_id: str) -> PluginRecord:
        return self._transition(plugin_id, PluginState.ENABLED)

    def disable(self, plugin_id: str) -> PluginRecord:
        return self._transition(plugin_id, PluginState.DISABLED)

    def remove(self, plugin_id: str) -> PluginRecord:
        rec = self._get(plugin_id)
        if rec.state == PluginState.ENABLED:
            self.disable(plugin_id)
        if rec.state not in (
            PluginState.DISABLED,
            PluginState.INSTALLED,
            PluginState.REJECTED,
            PluginState.FAILED_INSTALL,
        ):
            raise ValueError(f"removal ilegal dari {rec.state}")
        rec.state = PluginState.REMOVED
        rec.granted_permissions = frozenset()
        return rec

    # ------------------------------------------------------------ enforcement
    def check_permission(
        self, plugin_id: str, permission: str
    ) -> tuple[bool, str]:
        rec = self._plugins.get(plugin_id)
        if rec is None:
            return False, "plugin tidak terdaftar"
        if rec.state != PluginState.ENABLED:
            return False, f"plugin state={rec.state} (harus ENABLED)"
        if permission not in rec.granted_permissions:
            return False, f"izin {permission} tidak diberikan (default deny)"
        return True, "granted"

    def install_order(self) -> list[str]:
        """Urutan instalasi topologis atas plugin terdaftar (untuk buku/audit)."""
        g = Digraph()
        for pid in self._plugins:
            g.add_node(pid)
        for pid, rec in self._plugins.items():
            for dep in rec.manifest.dependencies:
                if dep in self._plugins:
                    g.add_edge(dep, pid)
        order = topological_order(g)
        return order if order else []

    # ---------------------------------------------------------------- util
    def _get(self, plugin_id: str) -> PluginRecord:
        rec = self._plugins.get(plugin_id)
        if rec is None:
            raise KeyError(plugin_id)
        return rec

    def _transition(self, plugin_id: str, target: str) -> PluginRecord:
        rec = self._get(plugin_id)
        key = (rec.state, target)
        if key not in _PLUGIN_TRANSITIONS:
            raise ValueError(f"transisi plugin ilegal: {rec.state} → {target}")
        rec.state = target
        return rec

    def report(self) -> list[dict[str, Any]]:
        return [
            {
                "plugin_id": r.manifest.plugin_id,
                "version": r.manifest.version,
                "state": r.state,
                "permissions": sorted(r.granted_permissions),
                "rejection_reason": r.rejection_reason,
            }
            for r in sorted(
                self._plugins.values(), key=lambda r: r.manifest.plugin_id
            )
        ]
