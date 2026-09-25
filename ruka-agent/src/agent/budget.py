"""Budget governor — lima sumbu, penolakan yang jujur.
INVARIAN: satu-satunya cara loop berhenti karena resource adalah
BudgetExceeded — bukan exception acak, bukan timeout socket, bukan
kelelahan. Hentian anggaran selalu membawa laporan.
"""
from __future__ import annotations
import time
from dataclasses import dataclass

class BudgetExceeded(RuntimeError):
    """Anggaran habis — bawa laporan, bukan penyesalan."""
    def __init__(self, axis: str, spent: object, limit: object,
                 report: str) -> None:
        super().__init__(
            f"Budget {axis} terlampaui: spent={spent}, limit={limit}. "
            f"Laporan: {report}"
        )
        self.axis, self.report = axis, report

@dataclass
class Budget:
    max_iterations: int = 12
    max_tokens: int = 60_000
    max_seconds: float = 240.0
    max_tool_calls: int = 25
    max_tasks: int = 3

@dataclass
class BudgetState:
    iterations: int = 0
    tokens: int = 0
    seconds: float = 0.0
    tool_calls: int = 0
    tasks: int = 1

class BudgetGovernor:
    def __init__(self, budget: Budget) -> None:
        self._budget = budget
        self.state = BudgetState()
        self._t0 = time.monotonic()

    def start_clock(self) -> None:
        self._t0 = time.monotonic()

    def check_iteration(self, progress_note: str = "") -> None:
        self.state.iterations += 1
        self._tick()
        if self.state.iterations > self._budget.max_iterations:
            raise BudgetExceeded(
                "iterations", self.state.iterations,
                self._budget.max_iterations,
                report=f"iterasi ke-{self.state.iterations}; progres: "
                       f"{progress_note or 'tidak ada progres terukur'}")

    def add_tokens(self, n: int) -> None:
        self.state.tokens += n
        if self.state.tokens > self._budget.max_tokens:
            raise BudgetExceeded("tokens", self.state.tokens,
                                 self._budget.max_tokens,
                                 report="konsumsi token melebihi jatah")

    def add_tool_call(self) -> None:
        self.state.tool_calls += 1
        if self.state.tool_calls > self._budget.max_tool_calls:
            raise BudgetExceeded("tool_calls", self.state.tool_calls,
                                 self._budget.max_tool_calls,
                                 report="pemanggilan tool melampaui jatah")

    def add_task(self) -> None:
        self.state.tasks += 1
        if self.state.tasks > self._budget.max_tasks:
            raise BudgetExceeded("tasks", self.state.tasks,
                                 self._budget.max_tasks,
                                 report="goal melebar menjadi tugas tambahan")

    def _tick(self) -> None:
        self.state.seconds = time.monotonic() - self._t0
        if self.state.seconds > self._budget.max_seconds:
            raise BudgetExceeded("seconds", round(self.state.seconds, 1),
                                 self._budget.max_seconds,
                                 report="waktu nyata sesi terlampaui")

    def pressure(self) -> dict[str, float]:
        """Rasio pemakaian per sumbu (0..1+) — untuk trace & UI."""
        self._tick()
        b, s = self._budget, self.state
        return {
            "iterations": s.iterations / b.max_iterations,
            "tokens": s.tokens / b.max_tokens,
            "seconds": s.seconds / b.max_seconds,
            "tool_calls": s.tool_calls / b.max_tool_calls,
            "tasks": s.tasks / b.max_tasks,
        }

    def is_pressured(self, threshold: float = 0.75) -> bool:
        return any(v >= threshold for v in self.pressure().values())
