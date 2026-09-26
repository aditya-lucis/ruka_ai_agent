# -*- coding: utf-8 -*-
"""Ruka's system self-model — facts, not sentience.
The self-model is a *queryable inventory of the running system*:
which model/provider serves the LLM core, which capabilities the
registry reports, which tools exist and with what permissions, how
memory and the session are doing, and what the known limitations are.
It is deliberately separate from persona: Ruka may *say* "vampire
memory" in conversation, but ``can_do("live_audio")`` must return the
registry's truth, and ``describe()`` must render capabilities the
patch edition's registry actually knows about. A self-model that
invents capabilities is a hallucination with a API.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Mapping, Sequence

@dataclass
class ToolStatus:
    name: str
    permission: str             # "allowed" | "denied" | "ask_user"
    risk: float = 0.0

@dataclass
class RukaSelfModel:
    model_id: str
    provider: str
    capabilities: set[str] = field(default_factory=set)
    tools: list[ToolStatus] = field(default_factory=list)
    memory_items: int = 0
    memory_kinds: Mapping[str, int] = field(default_factory=dict)
    session_id: str = ""
    current_task: str = ""
    known_limitations: tuple[str, ...] = ()

    # ------------------------------------------------------- queries
    def can_do(self, capability: str) -> tuple[bool, str]:
        """Grounded capability check: YES only if the registry says so."""
        if capability in self.capabilities:
            return True, f"capability '{capability}' is registered"
        return False, (f"capability '{capability}' is NOT registered — "
                       f"I must not claim it")

    def tool_permission(self, tool_name: str) -> str | None:
        for t in self.tools:
            if t.name == tool_name:
                return t.permission
        return None

    def capability_gaps(self, wanted: Sequence[str]) -> list[str]:
        return [c for c in wanted if c not in self.capabilities]

    def describe(self) -> str:
        """One honest paragraph: what I am, what I can and cannot do."""
        caps = ", ".join(sorted(self.capabilities)) or "none"
        tool_lines = ", ".join(
            f"{t.name}({t.permission})" for t in self.tools) or "none"
        limits = "; ".join(self.known_limitations) or "none recorded"
        
        return (
            f"System self-model — LLM core: {self.model_id} via {self.provider}. "
            f"Registered capabilities: {caps}. Tools: {tool_lines}. "
            f"Memory: {self.memory_items} items "
            f"({', '.join(f'{k}={v}' for k, v in sorted(self.memory_kinds.items())) or 'empty'}). "
            f"Session '{self.session_id or '-'}', current task: "
            f"{self.current_task or 'none'}. Known limitations: {limits}."
        )

    def user_facing_claims(self) -> list[str]:
        """What Ruka may honestly tell the user (persona-compatible)."""
        claims = []
        ok_live, _ = self.can_do("live_audio")
        ok_vision, _ = self.can_do("image_input")
        
        claims.append("I can read and write text (LLM core is online).")
        claims.append("I can remember across sessions (memory subsystem present)."
                      if self.memory_items > 0 or "memory" in self.capabilities
                      else "My memory is currently empty.")
                      
        if ok_vision:
            claims.append("I can look at images you show me.")
        else:
            claims.append("I cannot see images in this configuration.")
            
        if ok_live:
            claims.append("I can hold a live voice conversation.")
        else:
            claims.append("I cannot speak live in this configuration.")
            
        claims.append("I will say so plainly when I lack a capability.")
        return claims
