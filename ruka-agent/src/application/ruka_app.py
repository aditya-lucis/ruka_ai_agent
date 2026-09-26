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

# RUKA COGNITION VOLUME III IMPORTS
from src.ruka_cognition.neural import RuleBasedIntentClassifier
from src.ruka_cognition.observability import MetricsRecorder
from src.ruka_cognition.selfmodel import RukaSelfModel, ToolStatus

log = logging.getLogger("ruka.app")

class RukaApp:
    """Perakitan akhir: semua lapisan, satu titik komposisi (Crimson Cognition V3)."""
    def __init__(self):
        cfg = load_config()
        raw = genai.Client(api_key=cfg.api_key)
        client = GeminiClient(cfg)
        
        # lapisan observability & self-model (V3)
        self.metrics = MetricsRecorder()
        
        # lapisan tool
        registry = ToolRegistry()
        registry.register(CalculatorTool())
        registry.register(DateTimeTool())
        
        # bangun Self-Model deterministik (V3)
        self.self_model = RukaSelfModel(
            model_id=cfg.model,
            provider="Gemini",
            capabilities={"text_input", "text_output", "memory", "tools"},
            tools=[ToolStatus(name=t, permission="allowed") 
                   for t in ("calculator", "current_datetime")],
            session_id="ruka_cli_v3"
        )
        
        # lapisan cognition intent (V3)
        self.intent_clf = RuleBasedIntentClassifier()
        
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
        """Satu request end-to-end melalui seluruh stack dengan routing V3."""
        # 1. Deterministic Intent Classification
        pred = self.intent_clf.predict_one(request)
        self.metrics.record("intent_confidence", pred.confidence, 
                            tags={"intent": pred.label})
                            
        mem_ctx = self.memory.context_for(user_id, request)
        
        # 2. Routing berdasar intent (dengan prioritas self-model untuk pertanyaan identitas/kemampuan)
        req_lower = request.lower()
        self_keywords = (
            "kemampuan", "bisa apa", "fitur", "kapabilitas", 
            "apa saja kemampuan", "apa kemampuanmu", "siapa kamu", "identitas", "profil", "marquis"
        )
        if any(w in req_lower for w in self_keywords):
            claims = "\n".join(f"• {c}" for c in self.self_model.user_facing_claims())
            answer = (
                f"Kemampuan & Deskripsi Sistem Ruka:\n\n"
                f"{claims}\n\n"
                f"**Self-Model:** {self.self_model.describe()}"
            )
        elif pred.label == "chitchat":
            answer = self.client.complete(
                request,
                system_instruction="Anda adalah Ruka, Marquis dari Kekaisaran Trendamis. Sapa pengguna ('My Lord') dengan sopan, ekspresif, dan anggun."
            )
        elif pred.label == "lookup" or pred.label == "question":
            answer = self.rag.answer(request)
        else:
            # command / code_help -> Plan Runner
            answer = self.runner.run(
                f"{request}\n{mem_ctx}" if mem_ctx else request)
                
        # 3. Evaluasi
        if len(answer) > 800 and not answer.startswith("["):
            verdict = self.evaluator.evaluate(
                request, answer,
                ["akurat terhadap sumber", "lengkap", "jelas"],
            )
            if not verdict.passed:
                answer += ("\n\n[RUKA-EVAL] catatan: "
                           + "; ".join(verdict.issues))
                           
        # 4. Rekam Latency (Simulated untuk demo)
        self.metrics.record("turn_completed", 1.0)
        return answer
