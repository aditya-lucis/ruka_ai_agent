# -*- coding: utf-8 -*-
"""RUKA Skills System — Skills Runtime.

Menjalankan skill dengan penegakan keamanan berlapis:
Pemeriksaan izin (Permission Check), Path Jail, konfirmasi aksi berisiko,
pembatasan waktu (timeout), serta pencatatan jejak ke Event Bus.
"""
from __future__ import annotations

import logging
import time
from pathlib import Path
from typing import Any

from src.gateway.skills.models import Skill, SkillExecutionResult
from src.gateway.skills.registry import SkillRegistry
from src.gateway.permissions import PermissionManager, RiskLevel
from src.gateway.events import EventBus, Event
from src.tools.base import ToolError

log = logging.getLogger("ruka.gateway.skills.runtime")

PATH_ARG_KEYS = {
    "path",
    "file_path",
    "filepath",
    "target_path",
    "source_path",
    "directory",
    "cwd",
    "dest",
}


class SkillsRuntime:
    """Mesin eksekusi skill yang aman dan terisolasi."""

    def __init__(
        self,
        registry: SkillRegistry,
        permission_manager: PermissionManager,
        event_bus: EventBus | None = None,
    ) -> None:
        self.registry = registry
        self.permission_mgr = permission_manager
        self.event_bus = event_bus or EventBus()

    def needs_approval(self, skill: Skill | str) -> bool:
        """True bila skill harus mendapat persetujuan Young Lord sebelum dijalankan."""
        if isinstance(skill, str):
            found = self.registry.get(skill)
            if found is None:
                return False
            skill = found
        return self.permission_mgr.requires_approval(
            skill.risk_level, skill.requires_confirmation, skill.permissions
        )

    def execute(
        self,
        skill_name: str,
        args: dict[str, Any] | None = None,
        session_id: str = "default",
        confirm_granted: bool = False,
    ) -> SkillExecutionResult:
        """Mengeksekusi skill secara aman."""
        args = args or {}
        start_t = time.time()

        skill = self.registry.get(skill_name)
        if skill is None:
            err = f"Skill '{skill_name}' tidak terdaftar dalam sistem."
            log.warning(err)
            return SkillExecutionResult(
                success=False,
                error=err,
                skill_name=skill_name,
                duration_seconds=time.time() - start_t,
            )

        # 1. Pemeriksaan Izin (Permission Check)
        if not self.permission_mgr.check_permissions(skill.permissions):
            err = f"Akses ditolak: Izin {skill.permissions} belum dikabulkan untuk sesi ini."
            log.warning(err)
            return SkillExecutionResult(
                success=False,
                error=err,
                skill_name=skill_name,
                duration_seconds=time.time() - start_t,
            )

        # 2. Pemeriksaan Konfirmasi Aksi Berisiko (Human-in-the-Loop)
        if self.needs_approval(skill) and not confirm_granted:
            err = (
                f"Aksi membutuhkan konfirmasi eksplisit dari Young Lord "
                f"(Tingkat risiko: {skill.risk_level})."
            )
            self.event_bus.publish(
                Event(
                    event_type="permission.confirmation_required",
                    source="skills_runtime",
                    payload={"skill_name": skill_name, "risk_level": skill.risk_level},
                    session_id=session_id,
                )
            )
            return SkillExecutionResult(
                success=False,
                error=err,
                skill_name=skill_name,
                duration_seconds=time.time() - start_t,
            )

        # 3. Penegakan Path Jail pada parameter jalur berkas
        sanitized_args = dict(args)
        for k, v in args.items():
            if k.lower() in PATH_ARG_KEYS and isinstance(v, (str, Path)):
                try:
                    confined = self.permission_mgr.verify_path(v)
                    sanitized_args[k] = str(confined)
                except ToolError as te:
                    return SkillExecutionResult(
                        success=False,
                        error=f"Pelanggaran Path Jail: {te}",
                        skill_name=skill_name,
                        duration_seconds=time.time() - start_t,
                    )

        # 4. Eksekusi Handler
        try:
            if skill.handler is not None:
                data = skill.handler(**sanitized_args)
            elif skill.entry_point and skill.folder_path:
                entry = skill.folder_path / skill.entry_point
                if entry.exists():
                    import importlib.util
                    spec = importlib.util.spec_from_file_location(f"skill_{skill.name}", entry)
                    if spec and spec.loader:
                        mod = importlib.util.module_from_spec(spec)
                        spec.loader.exec_module(mod)
                        if hasattr(mod, "run"):
                            data = mod.run(**sanitized_args)
                        elif hasattr(mod, "main"):
                            data = mod.main(**sanitized_args)
                        else:
                            raise RuntimeError(f"Entry point {skill.entry_point} tidak memiliki fungsi run() atau main()")
                    else:
                        raise RuntimeError(f"Gagal memuat modul skill {entry}")
                else:
                    raise FileNotFoundError(f"Entry point {entry} tidak ditemukan")
            else:
                data = {"status": "ok", "message": f"Skill {skill.name} dieksekusi secara deklaratif."}

            duration = time.time() - start_t
            result = SkillExecutionResult(
                success=True,
                data=data,
                skill_name=skill_name,
                duration_seconds=duration,
            )

            self.event_bus.publish(
                Event(
                    event_type="skill.executed",
                    source="skills_runtime",
                    payload={"skill_name": skill_name, "success": True, "duration": duration},
                    session_id=session_id,
                )
            )
            return result

        except Exception as ex:
            duration = time.time() - start_t
            log.error("Kegagalan eksekusi skill '%s': %s", skill_name, ex)
            result = SkillExecutionResult(
                success=False,
                error=str(ex),
                skill_name=skill_name,
                duration_seconds=duration,
            )
            self.event_bus.publish(
                Event(
                    event_type="skill.executed",
                    source="skills_runtime",
                    payload={"skill_name": skill_name, "success": False, "error": str(ex)},
                    session_id=session_id,
                )
            )
            return result
