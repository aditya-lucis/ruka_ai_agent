from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from google import genai
from pydantic import BaseModel

from src.agent.evaluator import CodeEvaluator, EvaluationResult
from src.agent.project_memory import ProjectMemory
from src.agent.self_correction import SelfCorrectionManager
from src.config import Config
from src.domain.models import ToolDecision
from src.llm.structured import ask_structured
from src.tools.registry import ToolRegistry

log = logging.getLogger("ruka.agent")


@dataclass
class LoopStats:
    iterations: int = 0
    tool_calls: int = 0
    tool_errors: int = 0
    tool_error_names: list = field(default_factory=list)
    self_corrections: int = 0


class AgentOrchestrator:
    """Loop agentik stateless dengan lima penjaga keselamatan serta
    dukungan evaluasi kode & perbaikan mandiri (Self-Correction Loop - Phase 2).
    """

    def __init__(
        self,
        client: genai.Client,
        cfg: Config,
        registry: ToolRegistry,
        *,
        max_iterations: int = 8,
        max_tool_retries: int = 2,
        granted: set[str] | None = None,
        evaluator: CodeEvaluator | None = None,
        self_correction: SelfCorrectionManager | None = None,
        project_memory: ProjectMemory | None = None,
        mode: str = "hybrid",
    ):
        self.client = client
        self.cfg = cfg
        self.registry = registry
        self.mode = mode
        # Mode koding memerlukan batas iterasi yang lebih tinggi untuk workflow multi-step
        if mode == "coding" and max_iterations == 8:
            self.max_iterations = 20
        else:
            self.max_iterations = max_iterations

        self.max_tool_retries = max_tool_retries
        self.granted = granted or set()
        self.evaluator = evaluator
        self.self_correction = self_correction
        self.project_memory = project_memory
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

            fc_steps = [s for s in interaction.steps if s.type == "function_call"]

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

                # Evaluator & Self-Correction Hook (Phase 2)
                if self.evaluator:
                    eval_res = self.evaluator.evaluate_tool(
                        fc.name, dict(fc.arguments), outcome
                    )
                    if not eval_res.passed and self.self_correction:
                        if self.self_correction.should_correct(eval_res):
                            correction_prompt = (
                                self.self_correction.build_correction_prompt(
                                    fc.name, dict(fc.arguments), eval_res
                                )
                            )
                            history.append({
                                "type": "user_input",
                                "content": [{
                                    "type": "text",
                                    "text": correction_prompt,
                                }],
                            })
                            self.stats.self_corrections += 1
                            log.info("injeksi prompt koreksi mandiri ke riwayat percakapan")

            # PENJAGA 5: kegagalan berulang
            if self._repeating_failure():
                return self._stop("kegagalan tool berulang", history)

    def _guarded_execute(self, fc) -> dict:
        """PENJAGA 3+4: retry terbatas + tercatat."""
        self.stats.tool_calls += 1
        outcome = self.registry.execute(
            fc.name, dict(fc.arguments), granted=self.granted
        )
        if "error" in outcome:
            self.stats.tool_errors += 1
            self.stats.tool_error_names.append(fc.name)
        return outcome

    def _repeating_failure(self) -> bool:
        """Tool yang sama gagal >= 2x = pola, bukan kecelakaan."""
        if len(self.stats.tool_error_names) < 2:
            return False
        return len(set(self.stats.tool_error_names)) < len(
            self.stats.tool_error_names
        )

    def _stop(self, reason: str, history: list) -> str:
        log.warning("loop berhenti: %s (stats=%s)", reason, self.stats)
        return (
            f"[RUKA-STOP] {reason}. Iterasi: "
            f"{self.stats.iterations}, tool dipanggil: "
            f"{self.stats.tool_calls}, error: {self.stats.tool_errors}."
        )

    def _system_instruction(self) -> str:
        base = (
            "Anda Ruka, Marquis dari Trendamis — asisten teknis bangsawan berwibawa.\n"
            "Selesaikan tugas dengan tools yang tersedia bila perlu.\n"
            "Bila tugas selesai, jawab langsung TANPA memanggil tool.\n"
            "Bila tool gagal, pertimbangkan pendekatan lain daripada mengulanginya secara membabi buta.\n"
            "ATURAN LORE LOCK: Blok kode (```) harus 100% murni dan profesional tanpa narasi di dalamnya. "
            "Gaya bicara bangsawan vampir hanya muncul di luar blok kode."
        )

        extras: list[str] = []
        if self.project_memory:
            proj_ctx = self.project_memory.format_prompt_context()
            if proj_ctx:
                extras.append(proj_ctx)

        if extras:
            return f"{base}\n\n" + "\n\n".join(extras)
        return base
