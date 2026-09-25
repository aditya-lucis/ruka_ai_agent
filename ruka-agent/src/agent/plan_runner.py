from __future__ import annotations
import logging
from src.agent.orchestrator import AgentOrchestrator
from src.agent.planner import PlannerAgent
from src.domain.models import TaskPlan

log = logging.getLogger("ruka.plan_runner")

class PlanRunner:
    """Eksekusi TaskPlan langkah demi langkah dengan replan terbatas."""
    def __init__(self, planner: PlannerAgent, agent: AgentOrchestrator):
        self.planner = planner
        self.agent = agent

    def run(self, goal: str) -> str:
        plan = self.planner.plan(
            goal,
            available_tools=list(self.agent.registry._tools.keys()),
        )
        replans = 0
        results: list[str] = []
        
        while plan.steps:
            step = plan.steps[0]
            outcome = self.agent.run(
                f"Langkah {step.step_id} dari rencana '{plan.goal}': "
                f"{step.description}"
            )
            results.append(f"[{step.step_id}] {outcome}")
            
            if outcome.startswith("[RUKA-STOP]"):  # kegagalan
                if replans >= self.planner.max_replans:
                    return self._abort(goal, results,
                                       "batas replan tercapai")
                plan = self.planner.replan(plan, step, outcome)
                replans += 1
                log.warning("replan %d untuk '%s'", replans, goal)
            else:
                plan.steps.pop(0)  # langkah selesai
                
        return "\n\n".join(results)

    def _abort(self, goal, results, reason) -> str:
        log.error("plan abort: %s (%s)", goal, reason)
        return ("[RUKA-PLAN-ABORT] " + reason +
                "\nHasil sementara:\n" + "\n".join(results))
