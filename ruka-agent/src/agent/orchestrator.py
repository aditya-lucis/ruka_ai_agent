from __future__ import annotations
import json
import logging
from dataclasses import dataclass, field
from google import genai
from pydantic import BaseModel
from src.config import Config
from src.llm.structured import ask_structured
from src.tools.registry import ToolRegistry
from src.domain.models import ToolDecision

log = logging.getLogger("ruka.agent")

@dataclass
class LoopStats:
    iterations: int = 0
    tool_calls: int = 0
    tool_errors: int = 0
    tool_error_names: list = field(default_factory=list)

class AgentOrchestrator:
    """Loop agentik stateless dengan lima penjaga keselamatan."""
    def __init__(
        self,
        client: genai.Client,
        cfg: Config,
        registry: ToolRegistry,
        *,
        max_iterations: int = 8,
        max_tool_retries: int = 2,
        granted: set[str] | None = None,
    ):
        self.client = client
        self.cfg = cfg
        self.registry = registry
        self.max_iterations = max_iterations
        self.max_tool_retries = max_tool_retries
        self.granted = granted or set()
        self.stats = LoopStats()

    def run(self, user_request: str, *, history: list | None = None) -> str:
        history = history if history is not None else []
        history.append({
            "type": "user_input",
            "content": [{"type": "text", "text": user_request}],
        })
        
        system = self._system_instruction()
        
        while True:
            # PENJAGA 1: batas iterasi
            if self.stats.iterations >= self.max_iterations:
                return self._stop("batas iterasi tercapai", history)
            
            self.stats.iterations += 1
            
            interaction = self.client.interactions.create(
                model=self.cfg.model,
                store=False,
                input=history,
                tools=self.registry.declarations(),
                system_instruction=system,
            )
            
            for step in interaction.steps:
                history.append(step.model_dump())
            
            fc_steps = [s for s in interaction.steps 
                        if s.type == "function_call"]
            
            if not fc_steps:
                # PENJAGA 2: termination alami — model menjawab
                return interaction.output_text or "(kosong)"
            
            for fc in fc_steps:
                outcome = self._guarded_execute(fc)
                history.append({
                    "type": "function_result",
                    "name": fc.name,
                    "call_id": fc.id,
                    "result": [{
                        "type": "text",
                        "text": json.dumps(outcome),
                    }],
                })
            
            # PENJAGA 5: kegagalan berulang
            if self._repeating_failure():
                return self._stop("kegagalan tool berulang", history)

    def _guarded_execute(self, fc) -> dict:
        """PENJAGA 3+4: retry terbatas + tercatat."""
        self.stats.tool_calls += 1
        outcome = self.registry.execute(
            fc.name, dict(fc.arguments), granted=self.granted)
        if "error" in outcome:
            self.stats.tool_errors += 1
            self.stats.tool_error_names.append(fc.name)
        return outcome

    def _repeating_failure(self) -> bool:
        """Tool yang sama gagal >= 2x = pola, bukan kecelakaan."""
        if len(self.stats.tool_error_names) < 2:
            return False
        return len(set(self.stats.tool_error_names)) < len(
            self.stats.tool_error_names)

    def _stop(self, reason: str, history: list) -> str:
        log.warning("loop berhenti: %s (stats=%s)", reason, self.stats)
        return (
            f"[RUKA-STOP] {reason}. Iterasi: "
            f"{self.stats.iterations}, tool dipanggil: "
            f"{self.stats.tool_calls}, error: {self.stats.tool_errors}."
        )

    def _system_instruction(self) -> str:
        return (
            "Anda Ruka, asisten teknis. Selesaikan tugas dengan "
            "tools yang tersedia bila perlu. Bila tugas selesai, "
            "jawab langsung TANPA memanggil tool. Bila tool gagal, "
            "pertimbangkan pendekatan lain daripada mengulanginya."
        )
