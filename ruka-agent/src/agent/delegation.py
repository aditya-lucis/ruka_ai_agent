# -*- coding: utf-8 -*-
"""Specialist pool – delegasi eksplisit di bawah Ruka Core.
Spesialis = alat ber-domain: konteks sendiri, izin minimal,
budget turunan, hasil ter-typed. BUKAN agen yang saling mengobrol.
"""
from __future__ import annotations
import json
from dataclasses import dataclass, field
from typing import Any
from pydantic import BaseModel, Field
from src.agent.budget import Budget, BudgetGovernor
from src.capability.registry import Permission


class SpecialistVerdict(BaseModel):
    """Kontrak hasil – sama untuk semua spesialis."""
    specialist: str
    summary: str = Field(description="ringkasan 2-4 kalimat")
    key_findings: list[str] = Field(default_factory=list)
    confidence: float = Field(0.5, ge=0.0, le=1.0)


@dataclass(frozen=True)
class SpecialistSpec:
    name: str                      # "research" | "retrieval" | ...
    role_prompt: str               # system instruction spesifik
    allowed_permissions: frozenset[Permission]
    context_source: str            # korpus/lokasi konteks khusus
    share_of_budget: float = 0.3   # dipotong dari anggaran core


RESEARCH_SPEC = SpecialistSpec(
    name="research",
    role_prompt=("Anda spesialis riset: kumpulkan & sintesis fakta "
                 "dari sumber yang diberikan. Jangan menulis "
                 "rekomendasi akhir – itu tugas pemanggil."),
    allowed_permissions=frozenset({Permission.READ, Permission.NETWORK}),
    context_source="knowledge_base",
    share_of_budget=0.3,
)


@dataclass
class Delegation:
    spec: SpecialistSpec
    task: str
    result: SpecialistVerdict | None = None
    trace: list[dict] = field(default_factory=list)


class SpecialistPool:
    """Menjalankan delegasi dalam pagar: budget turunan + izin."""
    def __init__(self, client: Any, settings: Any, policy: Any, registry: Any) -> None:
        self._client = client
        self._settings = settings
        self._policy = policy                    # ToolPolicy (P15)
        self._registry = registry                # CapabilityRegistry (P14)

    def delegate(self, spec: SpecialistSpec, task: str,
                 core_budget: Budget) -> SpecialistVerdict:
        # 1. izin spesialis: kelas di luar jatahnya – tolak keras
        for perm in spec.allowed_permissions:
            decision = self._policy.decide(perm)
            if not decision.allowed:
                raise PermissionError(
                    f"spesialis {spec.name}: {decision.reason}")
        # 2. budget turunan – dipotong dari core, bukan tambahan
        sub = Budget(
            max_iterations=max(2, int(core_budget.max_iterations * spec.share_of_budget)),
            max_tokens=int(core_budget.max_tokens * spec.share_of_budget),
            max_seconds=core_budget.max_seconds * spec.share_of_budget,
            max_tool_calls=max(3, int(core_budget.max_tool_calls * spec.share_of_budget)),
            max_tasks=1,
        )
        governor = BudgetGovernor(sub)
        # 3. jalankan dengan struktur (structured output Vol I)
        interaction = self._client.interactions.create(
            model=self._settings.model,
            input=[{"type": "user_input",
                   "content": [{"type": "text", "text": task}]}],
            system_instruction=spec.role_prompt,
            response_format={"type": "text",
                             "mime_type": "application/json",
                             "schema": SpecialistVerdict.model_json_schema()},
            store=False)
        governor.add_tokens(len(interaction.output_text or "") // 4)
        verdict = SpecialistVerdict.model_validate_json(
            interaction.output_text or "{}")
        verdict = verdict.model_copy(update={"specialist": spec.name})
        return verdict

    def merge_into_history(self, d: Delegation) -> dict:
        """Hasil spesialis masuk history core sebagai function_result
        biasa – core tetap satu-satunya yang bernalar akhir."""
        assert d.result is not None
        payload = {
            "summary": d.result.summary,
            "key_findings": d.result.key_findings,
            "confidence": d.result.confidence,
        }
        return {
            "type": "function_result",
            "call_id": f"delegate:{d.spec.name}",
            "name": f"specialist_{d.spec.name}",
            "result": [{
                "type": "text",
                "text": json.dumps(payload, ensure_ascii=False)
            }]
        }


def as_tool_schema(spec: SpecialistSpec) -> dict:
    """Spesialis tampil di mata core sebagai SATU tool biasa."""
    return {
        "type": "function",
        "name": f"specialist_{spec.name}",
        "description": (f"Delegasikan sub-tugas ke spesialis "
                        f"{spec.name}. Gunakan hanya bila sub-tugas "
                        f"berkonteks luas dan terpisah."),
        "parameters": {
            "type": "object",
            "properties": {
                "task": {
                    "type": "string",
                    "description": "sub-tugas terbatas"
                }
            },
            "required": ["task"]
        }
    }
