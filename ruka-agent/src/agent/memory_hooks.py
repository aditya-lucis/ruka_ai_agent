from __future__ import annotations
from src.agent.orchestrator import AgentOrchestrator
from src.memory.manager import MemoryManager

def attach_memory(agent: AgentOrchestrator,
                  memory: MemoryManager,
                  user_id: str,
                  last_request: str) -> AgentOrchestrator:
    """Suntikkan konteks memori sebagai system extension."""
    base = agent._system_instruction()

    def system_with_memory() -> str:
        ctx = memory.context_for(user_id, last_request)
        return f"{base}\n\n{ctx}" if ctx else base

    agent._system_instruction = system_with_memory
    return agent
