# -*- coding: utf-8 -*-
"""Seven Ventricles of Crimson Heart (FR-HE-02 s/d FR-HE-07).

Tujuh simpul ventrikel agen di bawah kendali supervisor LangGraph:
1. Planner: Menyusun DAG 2-6 langkah asiklik
2. Researcher: Menjunjung hukum besi riset ber-URL
3. Coder: Menghasilkan EditProposal ber-anchor
4. Reviewer: Hak veto 4 segel (uji, cakupan >= 85%, gaya, OWASP)
5. DevOps: Build, health probes, dan rollback
6. ERP: Pelacakan tiket dan tugas
7. Browser: Interaksi web terizin
"""
from __future__ import annotations

import time
from typing import Any, Sequence

from src.heart.models import (
    DAGPlan,
    EditProposal,
    PlanStep,
    ReviewVerdict,
    VentricleRole,
)


class PlannerVentricle:
    def create_plan(self, task_id: str, objective: str, steps_data: Sequence[dict[str, Any]]) -> DAGPlan:
        """Menyusun rencana DAG asiklik 2 sampai 6 langkah."""
        steps = tuple(
            PlanStep(
                step_id=s["step_id"],
                ventricle=VentricleRole(s.get("ventricle", "coder")),
                description=s["description"],
                dependencies=tuple(s.get("dependencies", ())),
                estimated_tokens=s.get("estimated_tokens", 1000),
            )
            for s in steps_data
        )
        return DAGPlan(task_id=task_id, objective=objective, steps=steps)


class ResearcherVentricle:
    def conduct_research(self, topic: str, citations: Sequence[dict[str, str]]) -> dict[str, Any]:
        """Riset dengan kepatuhan hukum besi sitasi URL."""
        if not citations:
            raise ValueError("Hukum Besi Riset Dilanggar: Laporan tanpa sitasi sumber ditolak keras!")
        if len(citations) > 12:
            raise ValueError(f"Maksimal 12 halaman per pertanyaan riset, menerima {len(citations)}")
        return {
            "topic": topic,
            "citations_count": len(citations),
            "findings": f"Riset terverifikasi untuk {topic} dengan {len(citations)} sumber sah.",
        }


class CoderVentricle:
    def propose_edit(
        self,
        file_path: str,
        anchor_signature: str,
        new_content: str,
        reason: str,
        test_cmd: str,
    ) -> EditProposal:
        """Menghasilkan proposal edit ber-anchor 5-field."""
        if not file_path or not anchor_signature:
            raise ValueError("EditProposal membutuhkan file_path dan anchor_signature yang sah")
        return EditProposal(
            file_path=file_path,
            anchor_signature=anchor_signature,
            new_content=new_content,
            reason=reason,
            test_cmd=test_cmd,
        )


class ReviewerVentricle:
    def review(
        self,
        test_passed: bool,
        coverage_percent: float,
        style_clean: bool,
        security_clean: bool,
        feedback: str = "",
    ) -> ReviewVerdict:
        """Meninjau proposal kode dengan hak veto 4 segel."""
        return ReviewVerdict(
            test_passed=test_passed,
            coverage_percent=coverage_percent,
            style_clean=style_clean,
            security_clean=security_clean,
            feedback=feedback,
        )


class DevOpsVentricle:
    def deploy_and_probe(self, probes_success: Sequence[bool]) -> dict[str, Any]:
        """Menjalankan 3 health probe dalam jendela 120s."""
        if len(probes_success) != 3:
            raise ValueError("DevOps membutuhkan tepat 3 health probe")
        healthy = all(probes_success)
        return {
            "healthy": healthy,
            "probes_passed": sum(1 for p in probes_success if p),
            "rollback_triggered": not healthy,
        }


class ERPVentricle:
    def track_task(self, task_id: str, status: str, logged_hours: float) -> dict[str, Any]:
        return {"task_id": task_id, "status": status, "logged_hours": logged_hours}


class BrowserVentricle:
    def sandbox_navigate(self, url: str) -> dict[str, Any]:
        if not url.startswith(("http://", "https://")):
            raise ValueError("URL harus menggunakan protokol http atau https")
        return {"url": url, "status": "loaded"}
