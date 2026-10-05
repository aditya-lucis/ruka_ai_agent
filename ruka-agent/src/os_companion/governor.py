# -*- coding: utf-8 -*-
"""Resource Governor & Memory Watchdog (FR-OS-08).

Mengawasi konsumsi sumber daya RAM & GPU per organ:
- Anggaran RAM per organ dengan patroli setiap 60 detik
- Garis merah (redline) pada 90% dari kuota maksimal
- Tiga pelanggaran berturut-turut memicu restart organ
- Penurunan LOD avatar bila konsumsi grafis berlebihan
"""
from __future__ import annotations

import logging
from typing import Callable, Optional
from src.os_companion.models import OrganResourceQuota

log = logging.getLogger("ruka.os.governor")


class ResourceGovernor:
    REDLINE_RATIO = 0.90  # 90% dari kuota maksimal
    STRIKE_LIMIT = 3      # 3 pelanggaran beruntun

    def __init__(self) -> None:
        self.quotas: dict[str, OrganResourceQuota] = {}
        self.restart_handlers: dict[str, Callable[[str], bool]] = {}

    def register_organ_quota(
        self,
        organ_name: str,
        max_ram_mb: float,
        restart_fn: Optional[Callable[[str], bool]] = None,
    ) -> None:
        self.quotas[organ_name] = OrganResourceQuota(organ_name=organ_name, max_ram_mb=max_ram_mb)
        if restart_fn:
            self.restart_handlers[organ_name] = restart_fn

    def record_usage(self, organ_name: str, used_ram_mb: float) -> tuple[bool, bool]:
        """Mencatat penggunaan RAM organ terkini.

        Returns:
            (is_redline: bool, trigger_restart: bool)
        """
        quota = self.quotas.get(organ_name)
        if not quota:
            return False, False

        quota.current_ram_mb = used_ram_mb
        redline_mb = quota.max_ram_mb * self.REDLINE_RATIO

        if used_ram_mb >= redline_mb:
            quota.violation_count += 1
            log.warning(
                "Organ '%s' melanggar garis merah RAM: %.1f MB / %.1f MB (pelanggaran ke-%d)",
                organ_name, used_ram_mb, quota.max_ram_mb, quota.violation_count,
            )
            if quota.violation_count >= self.STRIKE_LIMIT:
                log.error("Organ '%s' mencapai 3 strike! Memulai prosedur restart otomatis.", organ_name)
                handler = self.restart_handlers.get(organ_name)
                if handler:
                    handler(organ_name)
                quota.violation_count = 0
                return True, True
            return True, False
        else:
            # Pulih normal, reset strike
            quota.violation_count = 0
            return False, False
