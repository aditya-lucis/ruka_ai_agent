# -*- coding: utf-8 -*-
"""Model & Tool Capability Registry — ruka-agent v0.3.1 (Patch Edition 1.1 + Vol II Part XIV).
Sumber kebenaran TUNGGAL untuk:
- Kapabilitas Model (Live, Thinking, Affective Dialog, Embeddings, Reasoning)
- Kapabilitas & Izin Tool (READ, WRITE, EXECUTE, NETWORK, DESTRUCTIVE)
- Self-Model & Identity Card (grounded facts)
"""
from __future__ import annotations
import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable

logger = logging.getLogger("ruka.capability")

# =====================================================================
# 1. TOOL CAPABILITIES & PERMISSIONS (PART XIV)
# =====================================================================

class Permission(str, Enum):
    READ = "read"
    WRITE = "write"
    EXECUTE = "execute"
    NETWORK = "network"
    DESTRUCTIVE = "destructive"

@dataclass(frozen=True)
class ToolIdentity:
    name: str
    description: str
    permission: Permission
    parameters: dict[str, Any]                    # JSON schema
    timeout_s: float = 15.0
    max_retries: int = 2
    rate_limit_per_min: int = 30
    is_multimodal: bool = False                   # hasil gambar (P11)

@dataclass
class ToolRecord:
    identity: ToolIdentity
    handler: Callable[..., Any]
    call_count: int = 0
    failure_count: int = 0
    last_used_at: float | None = None
    audit: list[dict[str, Any]] = field(default_factory=list)

    def log_call(self, args: dict, outcome: str, ms: float) -> None:
        self.call_count += 1
        self.last_used_at = time.time()
        if outcome == "failure":
            self.failure_count += 1
        self.audit.append({"args": args, "outcome": outcome, "ms": round(ms, 1)})
        if len(self.audit) > 200:                  # ring buffer 200 items
            self.audit = self.audit[-200:]

# =====================================================================
# 2. MODEL CAPABILITIES (PART IV / PATCH 1.1)
# =====================================================================

class CapabilityNotSupported(RuntimeError):
    """Kapabilitas wajib tidak tersedia pada model aktif — fail loud."""

@dataclass(frozen=True)
class ModelCapability:
    """Peta kapabilitas satu model ID (sumber: dokumentasi resmi)."""
    model_id: str
    api: str                       # "interactions" | "live" | "embed"
    text: bool
    image_input: bool
    audio_input: bool
    audio_output: bool = False     # native audio out (TTS/live)
    live: bool = False             # Live API (websocket dua arah)
    function_calling: bool = False
    structured_output: bool = False
    thinking_levels: tuple[str, ...] = ()
    affective_dialog: bool = False
    notes: str = ""

REGISTRY: dict[str, ModelCapability] = {
    "gemini-3.6-flash": ModelCapability(
        model_id="gemini-3.6-flash", api="interactions",
        text=True, image_input=True, audio_input=True,
        function_calling=True, structured_output=True,
        thinking_levels=("low", "medium", "high"),
        notes="model kerja utama (reasoning/agentic); BUKAN model Live API"),
    "gemini-3.8-flash": ModelCapability(
        model_id="gemini-3.8-flash", api="interactions",
        text=True, image_input=True, audio_input=True,
        function_calling=True, structured_output=True,
        thinking_levels=("low", "medium", "high"),
        notes="frontier flash model; reasoning/agentic"),
    "gemini-3.5-flash": ModelCapability(
        model_id="gemini-3.5-flash", api="interactions",
        text=True, image_input=True, audio_input=True,
        function_calling=True, structured_output=True,
        thinking_levels=("low", "medium", "high"),
        notes="seri stabil sebelumnya"),
    "gemini-3.1-flash-live-preview": ModelCapability(
        model_id="gemini-3.1-flash-live-preview", api="live",
        text=True, image_input=True, audio_input=True, audio_output=True,
        live=True, function_calling=True,
        thinking_levels=("minimal", "low", "medium", "high"),
        affective_dialog=False,
        notes="model Live API utama; FC sequential"),
    "gemini-2.5-flash-live-preview": ModelCapability(
        model_id="gemini-2.5-flash-live-preview", api="live",
        text=True, image_input=True, audio_input=True, audio_output=True,
        live=True, function_calling=True, affective_dialog=True,
        notes="satu-satunya jalur affective dialog saat ini"),
    "gemini-3.1-flash-tts-preview": ModelCapability(
        model_id="gemini-3.1-flash-tts-preview", api="interactions",
        text=True, image_input=False, audio_input=False, audio_output=True,
        notes="TTS satu/multi-pembicara via response_format audio"),
    "gemini-embedding-001": ModelCapability(
        model_id="gemini-embedding-001", api="embed",
        text=True, image_input=False, audio_input=False,
        notes="embed dokumen/query RAG"),
    "gemini-embedding-2-preview": ModelCapability(
        model_id="gemini-embedding-2-preview", api="embed",
        text=True, image_input=True, audio_input=True,
        notes="embedding multimodal (preview)"),
}

# =====================================================================
# 3. UNIFIED CAPABILITY REGISTRY
# =====================================================================

class CapabilityRegistry:
    """Gerbang tunggal: kapabilitas model & alat."""
    def __init__(self, registry: dict[str, ModelCapability] | None = None,
                 sdk_fields: set[str] | frozenset[str] | None = None) -> None:
        self._registry = registry if registry is not None else REGISTRY
        self._tools: dict[str, ToolRecord] = {}
        
        if sdk_fields is not None:
            self._sdk_fields = frozenset(sdk_fields)
        else:
            try:
                from google.genai import types
                self._sdk_fields = frozenset(
                    types.LiveConnectConfig.model_fields.keys())
            except Exception:
                self._sdk_fields = frozenset()

    # --- Tool Registry API ---
    def register(self, identity: ToolIdentity,
                 handler: Callable[..., Any]) -> None:
        if identity.name in self._tools:
            raise ValueError(f"tool duplikat: {identity.name}")
        self._tools[identity.name] = ToolRecord(identity, handler)

    def get(self, name: str) -> ToolRecord:
        rec = self._tools.get(name)
        if rec is None:
            raise KeyError(f"tool tak terdaftar: {name}")
        return rec

    def schemas_for_llm(self, names: list[str] | None = None) -> list[dict[str, Any]]:
        """Bentuk tools=[...] untuk Interactions API (Vol I)."""
        records = ([self.get(n) for n in names] if names
                   else list(self._tools.values()))
        return [{
            "type": "function",
            "name": r.identity.name,
            "description": r.identity.description,
            "parameters": r.identity.parameters,
        } for r in records]

    def capability_statement(self) -> dict[str, list[str]]:
        """Untuk self-model (PART 3): apa yang bisa & tidak bisa."""
        by_perm: dict[str, list[str]] = {}
        for r in self._tools.values():
            by_perm.setdefault(r.identity.permission.value, []).append(
                r.identity.name)
        return by_perm

    def health(self) -> list[dict[str, Any]]:
        """Untuk trace: kesehatan tiap tool (PART 23)."""
        return [{
            "name": r.identity.name,
            "calls": r.call_count,
            "failures": r.failure_count,
            "failure_rate": (r.failure_count / r.call_count
                             if r.call_count else 0.0),
        } for r in self._tools.values()]

    # --- Model Capability API ---
    def capability(self, model_id: str) -> ModelCapability:
        entry = self._registry.get(model_id)
        if entry is None:
            return ModelCapability(
                model_id=model_id, api="interactions",
                text=True, image_input=False, audio_input=False,
                notes="model tidak dikenal registry — diasumsikan text-only")
        return entry

    def supports(self, model_id: str, feature: str) -> bool:
        cap = self.capability(model_id)
        return bool(getattr(cap, feature, False))

    def require(self, model_id: str, feature: str) -> None:
        """Fail-loud untuk kapabilitas WAJIB (bukan opsional)."""
        if not self.supports(model_id, feature):
            raise CapabilityNotSupported(
                f"model '{model_id}' tidak mendukung '{feature}' "
                f"(registry: {self.capability(model_id).notes})")

    def sdk_knows(self, field_name: str) -> bool:
        return field_name in self._sdk_fields

    def live_config_extras(self, model_id: str, affective: bool
                           ) -> dict[str, object]:
        if not affective:
            return {}
        if not self.supports(model_id, "affective_dialog"):
            logger.warning(
                "affective dialog DIMINTA tapi tidak didukung '%s' — fallback",
                model_id)
            return {}
        if not self.sdk_knows("enable_affective_dialog"):
            logger.warning("SDK tidak mengenal field enable_affective_dialog")
            return {}
        return {"enable_affective_dialog": True}

    def explain(self, model_id: str) -> str:
        c = self.capability(model_id)
        flags = [f for f in ("live", "affective_dialog", "structured_output",
                             "function_calling") if getattr(c, f)]
        return (f"{c.model_id}: api={c.api} flags={flags or ['text-only']} "
                f"notes='{c.notes}'")

def default_registry() -> CapabilityRegistry:
    return CapabilityRegistry()
