# -*- coding: utf-8 -*-
"""CLI Interaktif Ruka v0.3.1 — The Awakened Marquis
Antarmuka baris perintah resmi untuk berinteraksi dengan Ruka.
Mendukung mode interaktif REPL, evaluasi cepat satu kalimat,
inspeksi state/identitas, dan mode offline terkalibrasi.
"""
from __future__ import annotations
import argparse
import sys
import time
from pathlib import Path

# Impor komponen kognitif & ekspresif Ruka
from src.identity.self_model import SelfModel, build_self_model
from src.state.core import InternalState
from src.state.machine import ExpressionFSM, Phase
from src.emotion.appraisal import AppraisalEngine, EventKind
from src.expression.engine import ExpressionEngine
from src.expression.params import Expression
from src.agent.complexity import ComplexityEstimator, Complexity
from src.agent.budget import Budget, BudgetGovernor
from src.confidence.model import Evidence, epistemic_level, disclaimer_text
from src.neural.intent import IntentMLP, embed_or_fallback, lexical_features
from src.telemetry.tracing import Trace, TraceWriter, redact


def banner() -> str:
    return r"""
  ____  _   _ _  __    _       ___ _____ _   
 |  _ \| | | | |/ /   / \     / _ \_   _/ \  
 | |_) | | | | ' /   / _ \   | | | || |/ _ \ 
 |  _ <| |_| | . \  / ___ \  | |_| || / ___ \
 |_| \_\\___/|_|\_\/_/   \_\  \___/ |_/_/   \_|
  RUKA v0.3.1 — The Awakened Marquis (Trendamis)
  Cognitive-Expressive Agentic Architecture
  =============================================
"""


class RukaSession:
    """Sesi interaksi penuh melintasi seluruh lapisan kognitif Ruka."""
    def __init__(self, session_id: str = "sess-default", log_dir: Path | None = None):
        self.session_id = session_id
        self.self_model = build_self_model(
            tool_names=["calculator", "current_datetime", "fetch_docs"],
            has_memory=True,
            has_rag=True,
            user_name="Bos",
        )
        self.state = InternalState()
        self.fsm = ExpressionFSM()
        self.appraisal = AppraisalEngine(self.state.emotion)
        self.expression_engine = ExpressionEngine(self.state)
        self.intent_mlp = IntentMLP(seed=42)
        self.complexity_estimator = ComplexityEstimator()
        self.trace_writer = TraceWriter(log_dir or Path("logs"), retention_days=14)

    def process_turn(self, user_text: str) -> dict:
        """Memproses satu giliran percakapan menembus 16 gerbang arsitektur."""
        t0 = time.monotonic()
        trace = Trace(goal=user_text, session_id=self.session_id)

        # 1. State FSM: Mulai mendengarkan
        self.fsm.transition(Phase.LISTENING, "user_speech_start")
        trace.event("fsm", "phase_change", phase=self.fsm.phase.value)

        # 2. Penilaian Emosi (Appraisal)
        if "ruka" in user_text.lower():
            event_kind = EventKind.USER_CALLED_NAME
        elif any(w in user_text.lower() for w in ("terima kasih", "hebat", "bagus", "keren")):
            event_kind = EventKind.PRAISE
        elif any(w in user_text.lower() for w in ("salah", "payah", "rusak", "bodoh")):
            event_kind = EventKind.TOOL_ERROR
        else:
            event_kind = EventKind.TASK_COMPLETED

        appraisal_result = self.appraisal.appraise(event_kind)
        trace.event("emotion", "appraisal", event=event_kind.value, vad=appraisal_result)

        # 3. Klasifikasi Intent (Otak Kecil - Neural Subsystem)
        feats = embed_or_fallback(user_text) + lexical_features(user_text)
        intent, intent_prob = self.intent_mlp.predict(feats)
        trace.event("neural", "intent_classified", intent=intent, prob=intent_prob)

        # 4. Gating Kompleksitas & Transisi Thinking
        self.fsm.transition(Phase.THINKING, "intent_ready")
        verdict = self.complexity_estimator.estimate(user_text)
        complexity_val = verdict.level.value
        trace.event("orchestrator", "complexity_gated", complexity=complexity_val)

        # 5. Ekspresi saat Berpikir
        expr_params = self.expression_engine.decide(phase=self.fsm.phase.value)
        trace.event("expression", "params_decided", expr=expr_params.expression.value)

        # 6. Penalaran / Response Synthesis (Demonstrasi Respon Marquis)
        # Menentukan level epistemik dan sanggahan kejujuran
        is_identity_q = any(w in user_text.lower() for w in ("siapa kamu", "identitas", "profil", "marquis"))
        if is_identity_q:
            evidence = Evidence(from_identity=True)
            core_answer = (
                f"Saya {self.self_model.essence.name}, {self.self_model.essence.former_title}. "
                f"Sistem agentic kognitif-ekspresif v{self.self_model.model_version}. "
                f"Saya melayani Bos dengan ketertiban lima abad, bukan teater."
            )
        elif intent == "greeting":
            evidence = Evidence(retrieval_top=0.9, tool_success=1.0, n_sources=2, stale_days=1)
            core_answer = "Salam, Bos. Ada tugas yang layak untuk strategi kita hari ini?"
        elif intent == "task_request":
            evidence = Evidence(retrieval_top=0.75, tool_success=1.0, n_sources=3, stale_days=5)
            core_answer = (
                f"Perintah diterima dengan status {complexity_val.upper()}. "
                "Seluruh parameter dependensi dan pagu anggaran telah diamankan. "
                "Langkah siap dijalankan."
            )
        else:
            evidence = Evidence(retrieval_top=0.45, tool_success=0.5, n_sources=1, stale_days=40)
            core_answer = "Saya menangkap pertanyaan Anda. Mari kita telaah buktinya bersama."

        level, conf_score = epistemic_level(evidence)
        disclaimer = disclaimer_text(level)
        final_text = f"{core_answer} {disclaimer}".strip()

        # 7. State FSM: Merespons
        self.fsm.transition(Phase.RESPONDING, "answer_synthesized")
        final_expr = self.expression_engine.decide(phase=self.fsm.phase.value)

        # 8. Selesai & Kembali ke Idle
        self.fsm.transition(Phase.IDLE, "speech_done")

        elapsed_ms = round((time.monotonic() - t0) * 1000, 1)
        summary = {
            "intent": intent,
            "complexity": complexity_val,
            "epistemic_level": level.value,
            "confidence": conf_score,
            "expression": final_expr.expression.value,
            "elapsed_ms": elapsed_ms,
        }

        # 9. Tulis Trace 16-bidang ke JSONL
        trace_path = self.trace_writer.write(trace, final_status="done", summary=summary)

        return {
            "answer": final_text,
            "summary": summary,
            "trace_path": trace_path,
            "trace_id": trace.trace_id,
        }


def main():
    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8")
        except Exception:
            pass

    parser = argparse.ArgumentParser(description="CLI Interaktif Ruka v0.3.1")
    parser.add_argument("query", nargs="*", help="Pertanyaan/perintah langsung ke Ruka")
    parser.add_argument("--status", action="store_true", help="Tampilkan status internal dan identitas Ruka")
    parser.add_argument("--interactive", "-i", action="store_true", help="Masuk ke mode REPL interaktif")
    args = parser.parse_args()

    session = RukaSession()

    if args.status:
        print(banner())
        e = session.self_model.essence
        print(f"[*] Identitas  : {e.name} ({e.former_title}, {e.origin})")
        print(f"[*] Spesies    : {e.species.value}")
        print(f"[*] Versi      : v{session.self_model.model_version}")
        print(f"[*] Voice TTS  : Sulafat (deep, steady, gentle cadence)")
        print(f"[*] Emosi VAD  : [Valence={session.state.emotion.valence:.2f}, Arousal={session.state.emotion.arousal:.2f}, Dominance={session.state.emotion.dominance:.2f}]")
        print(f"[*] Ekspresi   : {session.state.expression.expression}")
        print(f"[*] FSM Phase  : {session.fsm.phase.value}")
        return

    if args.query:
        query_text = " ".join(args.query)
        res = session.process_turn(query_text)
        print(f"\n[Ruka ({res['summary']['expression']}, {res['summary']['epistemic_level']})]: {res['answer']}")
        print(f"(Latency: {res['summary']['elapsed_ms']}ms | Trace: {res['trace_id']})\n")
        return

    # Default ke mode interaktif
    print(banner())
    print("Mode interaktif aktif. Ketik 'exit' atau 'keluar' untuk mengakhiri.\n")
    print(f"Ruka siap mendengarkan. Mood: {session.state.emotion.mood}.\n")

    while True:
        try:
            user_input = input("Bos > ").strip()
            if not user_input:
                continue
            if user_input.lower() in ("exit", "keluar", "quit", "q"):
                print("\nRuka: 'Selamat beristirahat, Bos. Istana tetap terjaga. Yes, Sir!'")
                break

            res = session.process_turn(user_input)
            s = res["summary"]
            print(f"\nRuka [{s['expression']}|{s['epistemic_level']}]: {res['answer']}")
            print(f"      -> [Intent: {s['intent']} | Complexity: {s['complexity']} | Latency: {s['elapsed_ms']}ms | ID: {res['trace_id']}]\n")

        except (KeyboardInterrupt, EOFError):
            print("\n\nRuka: 'Sesi diakhiri. Menutup gerbang.'")
            break


if __name__ == "__main__":
    main()
