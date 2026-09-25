from __future__ import annotations
import logging
from google import genai
from src.agent.evaluator import EvaluatorAgent
from src.agent.orchestrator import AgentOrchestrator
from src.agent.plan_runner import PlanRunner
from src.agent.planner import PlannerAgent
from src.config import load_config
from src.infrastructure.sqlite_store import SqliteMemoryStore
from src.llm.gemini_client import GeminiClient
from src.memory.manager import MemoryManager
from src.retrieval.embedder import GeminiEmbedder
from src.retrieval.rag import RAGPipeline
from src.retrieval.store import VectorStore
from src.tools.builtin import CalculatorTool, DateTimeTool
from src.tools.registry import ToolRegistry

log = logging.getLogger("ruka.app")

class RukaApp:
    """Perakitan akhir: semua lapisan, satu titik komposisi."""
    def __init__(self):
        cfg = load_config()
        raw = genai.Client(api_key=cfg.api_key)
        client = GeminiClient(cfg)
        
        # lapisan tool
        registry = ToolRegistry()
        registry.register(CalculatorTool())
        registry.register(DateTimeTool())
        
        # lapisan memory + persistence
        store = SqliteMemoryStore("ruka.db")
        memory = MemoryManager(store, client)
        
        # lapisan retrieval
        embedder = GeminiEmbedder(raw)
        vectors = VectorStore(dim=768)
        rag = RAGPipeline(embedder, vectors, client)
        
        # lapisan agent
        orchestrator = AgentOrchestrator(
            raw, cfg, registry, granted={"calculator", "current_datetime"})
        planner = PlannerAgent(client)
        runner = PlanRunner(planner, orchestrator)
        evaluator = EvaluatorAgent(client)
        
        self.cfg = cfg
        self.client = client
        self.memory = memory
        self.rag = rag
        self.runner = runner
        self.evaluator = evaluator
        self.orchestrator = orchestrator

    def handle(self, user_id: str, request: str) -> str:
        """Satu request end-to-end melalui seluruh stack."""
        mem_ctx = self.memory.context_for(user_id, request)
        
        # routing: pertanyaan knowledge base -> RAG
        if self._looks_like_kb_question(request):
            answer = self.rag.answer(request)
        else:
            answer = self.runner.run(
                f"{request}\n{mem_ctx}" if mem_ctx else request)
                
        # evaluasi hanya untuk artefak panjang (biaya sadar)
        if len(answer) > 800 and not answer.startswith("["):
            verdict = self.evaluator.evaluate(
                request, answer,
                ["akurat terhadap sumber", "lengkap", "jelas"],
            )
            if not verdict.passed:
                answer += ("\n\n[RUKA-EVAL] catatan: "
                           + "; ".join(verdict.issues))
        return answer

    @staticmethod
    def _looks_like_kb_question(text: str) -> bool:
        markers = ("menurut dokumen", "di knowledge base",
                   "dari arsip", "sumber kita")
        return any(m in text.lower() for m in markers)
