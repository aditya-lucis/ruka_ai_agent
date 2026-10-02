# -*- coding: utf-8 -*-
"""Plan Transparency: Transparansi rencana eksekusi bergaya bangsawan (Phase 3).
Menampilkan rencana bertahap, status progres eksekusi (Pending, Running, Done, Failed),
serta ringkasan hasil secara transparan kepada Young Lord sebelum dan sesudah eksekusi.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from src.domain.models import PlanStep, TaskPlan

log = logging.getLogger("ruka.agent.plan_transparency")


class StepStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class StepState:
    step: PlanStep
    status: StepStatus = StepStatus.PENDING
    result_summary: str = ""
    duration_s: float = 0.0


class PlanTransparency:
    """Manajer transparansi rencana kerja (Plan Transparency) Ruka."""

    STATUS_ICONS = {
        StepStatus.PENDING: "○",
        StepStatus.RUNNING: "◐",
        StepStatus.COMPLETED: "●",
        StepStatus.FAILED: "✕",
        StepStatus.SKIPPED: "⊝",
    }

    STATUS_LABELS_ARISTOCRAT = {
        StepStatus.PENDING: "Menanti giliran",
        StepStatus.RUNNING: "Sedang dikerjakan...",
        StepStatus.COMPLETED: "Selesai sempurna",
        StepStatus.FAILED: "Terkendala masalah",
        StepStatus.SKIPPED: "Dilewati",
    }

    def __init__(self, plan: TaskPlan):
        self.plan = plan
        self.states: list[StepState] = [
            StepState(step=s) for s in plan.steps
        ]
        self.current_index: int = 0

    def format_plan_announcement(self) -> str:
        """Format pengumuman rencana awal bergaya Marquis of Trendamis."""
        lines = [
            f"Hmm... Young Lord, hamba telah menyusun strategi kerja yang seksama untuk sasaran:",
            f"« {self.plan.goal} »\n",
            "Berikut rancangan langkah yang akan hamba tempuh:",
        ]
        for s in self.states:
            tool_note = f" (Alat: `{s.step.requires_tool}`)" if s.step.requires_tool else ""
            lines.append(f"  {s.step.step_id}. {s.step.description}{tool_note}")

        if self.plan.notes:
            lines.append(f"\nCatatan Khusus: {self.plan.notes}")

        lines.append(
            "\nApakah My Lord berkenan hamba segera mengeksekusi tahapan pertama?"
        )
        return "\n".join(lines)

    def mark_step_running(self, step_id: int) -> None:
        """Menandai langkah tertentu sedang berjalan."""
        for s in self.states:
            if s.step.step_id == step_id:
                s.status = StepStatus.RUNNING
                log.info("Langkah %d: RUNNING", step_id)

    def mark_step_completed(self, step_id: int, summary: str = "", duration_s: float = 0.0) -> None:
        """Menandai langkah tertentu selesai dengan sukses."""
        for s in self.states:
            if s.step.step_id == step_id:
                s.status = StepStatus.COMPLETED
                s.result_summary = summary
                s.duration_s = duration_s
                log.info("Langkah %d: COMPLETED", step_id)

    def mark_step_failed(self, step_id: int, error: str = "") -> None:
        """Menandai langkah tertentu gagal."""
        for s in self.states:
            if s.step.step_id == step_id:
                s.status = StepStatus.FAILED
                s.result_summary = error
                log.warning("Langkah %d: FAILED (%s)", step_id, error)

    def render_progress_markdown(self) -> str:
        """Render tampilan tabel progres untuk Markdown / Chat UI."""
        completed_count = sum(1 for s in self.states if s.status == StepStatus.COMPLETED)
        total = len(self.states)
        percent = int((completed_count / total) * 100) if total else 100

        lines = [
            f"**Status Kemajuan Eksekusi Rencana:** [{completed_count}/{total} Langkah — {percent}%]",
        ]
        for s in self.states:
            icon = self.STATUS_ICONS[s.status]
            status_desc = self.STATUS_LABELS_ARISTOCRAT[s.status]
            dur_str = f" ({s.duration_s:.1f}s)" if s.duration_s > 0 else ""
            lines.append(f"- {icon} **Langkah {s.step.step_id}**: {s.step.description} — *{status_desc}*{dur_str}")
            if s.result_summary and s.status in (StepStatus.COMPLETED, StepStatus.FAILED):
                lines.append(f"  > _{s.result_summary[:120]}_")

        return "\n".join(lines)

    def render_progress_cli(self, use_color: bool = True) -> str:
        """Render tampilan teks terminal berwarna ANSI."""
        cyan = "\033[96m" if use_color else ""
        green = "\033[92m" if use_color else ""
        red = "\033[91m" if use_color else ""
        yellow = "\033[93m" if use_color else ""
        bold = "\033[1m" if use_color else ""
        dim = "\033[2m" if use_color else ""
        reset = "\033[0m" if use_color else ""

        lines = [f"{cyan}{bold}┌── Rencana Kerja Marquis Ruka ──┐{reset}"]
        for s in self.states:
            if s.status == StepStatus.COMPLETED:
                badge = f"{green}[✓]{reset}"
            elif s.status == StepStatus.RUNNING:
                badge = f"{yellow}[⧖]{reset}"
            elif s.status == StepStatus.FAILED:
                badge = f"{red}[✕]{reset}"
            else:
                badge = f"{dim}[ ]{reset}"

            tool = f" {dim}({s.step.requires_tool}){reset}" if s.step.requires_tool else ""
            lines.append(f"  {badge} {bold}{s.step.step_id}.{reset} {s.step.description}{tool}")

        lines.append(f"{cyan}{bold}└────────────────────────────────┘{reset}")
        return "\n".join(lines)

    def format_final_report(self) -> str:
        """Laporan penutup eksekusi rencana menyeluruh."""
        failed = [s for s in self.states if s.status == StepStatus.FAILED]
        if not failed:
            return (
                "Seluruh tahapan telah diselesaikan dengan presisi dan kehormatan, Young Lord. "
                "Kode dan tugas kini siap untuk My Lord periksa."
            )
        fail_desc = ", ".join(f"Langkah {s.step.step_id}" for s in failed)
        return (
            f"Dengan berat hati hamba laporkan bahwa terdapat kendala pada {fail_desc}. "
            "Hamba telah menghentikan eksekusi sebelum menimbulkan anomali lebih lanjut. "
            "Apakah My Lord berkenan memberikan petunjuk tambahan?"
        )
