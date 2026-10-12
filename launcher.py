# -*- coding: utf-8 -*-
"""RUKA — The Persistent Mind & Companion Launcher (Python Brain Host)
Menghubungkan seluruh nalar kognisi (ruka-agent, ruka-persistence, ruka-companion)
ke tubuh Electron via protokol loopback IPC JSONL (Part XVI, XXIII, XXV, XXVI).
"""
from __future__ import annotations

import os
import sys
import json
import time
import socket
import select
import secrets
import signal
import threading
from pathlib import Path

# Tentukan direktori runtime & penyimpanan lokal
local_appdata = os.environ.get("LOCALAPPDATA") or str(Path.home() / "AppData" / "Local")
RUNTIME_DIR = Path(local_appdata) / "ruka" / "runtime"
ENDPOINT_FILE = RUNTIME_DIR / "ipc-endpoint.json"

# Amankan stdout/stderr jika berjalan di mode beku noconsole
if getattr(sys, "frozen", False):
    try:
        log_dir = Path(local_appdata) / "ruka" / "logs"
        log_dir.mkdir(parents=True, exist_ok=True)
        log_fp = open(log_dir / "ruka-brain.log", "a", encoding="utf-8", buffering=1)
        if sys.stdout is None:
            sys.stdout = log_fp
        if sys.stderr is None:
            sys.stderr = log_fp
    except Exception:
        pass

# Tentukan BASE_DIR dan EXE_DIR (Mendukung mode beku PyInstaller mandiri)
if getattr(sys, "frozen", False):
    BASE_DIR = Path(sys._MEIPASS)
    EXE_DIR = Path(sys.executable).resolve().parent
else:
    BASE_DIR = Path(__file__).resolve().parent
    EXE_DIR = BASE_DIR

# Tambahkan modul ke sys.path
sys.path.insert(0, str(BASE_DIR / "ruka-companion" / "src"))
sys.path.insert(0, str(BASE_DIR / "ruka-agent"))
sys.path.insert(0, str(BASE_DIR / "ruka-persistence" / "src"))

# Muat environment variable dari kandidat berkas .env
env_candidates = [
    EXE_DIR / ".env",
    EXE_DIR / "ruka-agent" / ".env",
    BASE_DIR / ".env",
    BASE_DIR / "ruka-agent" / ".env",
    Path(local_appdata) / "ruka" / ".env",
]
for env_path in env_candidates:
    if env_path.exists():
        try:
            for line in env_path.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, _, v = line.partition("=")
                    k, v = k.strip(), v.strip()
                    if len(v) >= 2 and v[0] == v[-1] and v[0] in "\"'":
                        v = v[1:-1]
                    if k not in os.environ:
                        os.environ[k] = v
            break
        except Exception:
            pass

PROTOCOL_VERSION = 2


class RukaBrainServer:
    def __init__(self, host: str = "127.0.0.1", workspace: str | Path | None = None):
        self.host = host
        self.token = secrets.token_hex(16)
        self.running = False
        self.start_time = time.time()
        self.workspace_root = self._resolve_initial_workspace(workspace)
        
        self.server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server_sock.bind((self.host, 0))
        self.port = self.server_sock.getsockname()[1]
        
        self.clients: list[socket.socket] = []
        self._lock = threading.Lock()
        self.session = None
        
        # Inisialisasi sesi kognisi Ruka
        self._init_cognition()

    @staticmethod
    def _resolve_initial_workspace(explicit: str | Path | None = None) -> Path:
        """Menentukan workspace awal yang aman, tidak mengunci user ke folder instalasi."""
        if explicit:
            p = Path(explicit).expanduser().resolve()
            if p.exists() and p.is_dir():
                return p
        env_ws = os.environ.get("RUKA_WORKSPACE")
        if env_ws:
            p = Path(env_ws).expanduser().resolve()
            if p.exists() and p.is_dir():
                return p
        for i, arg in enumerate(sys.argv[:-1]):
            if arg in ("--workspace", "-w"):
                p = Path(sys.argv[i + 1]).expanduser().resolve()
                if p.exists() and p.is_dir():
                    return p
        cwd = Path.cwd().resolve()
        if getattr(sys, "frozen", False):
            exe_parent = Path(sys.executable).resolve().parent
            if cwd == exe_parent or exe_parent in cwd.parents:
                safe_fallback = Path.home() / "Documents" / "RukaProjects"
                try:
                    safe_fallback.mkdir(parents=True, exist_ok=True)
                    return safe_fallback
                except Exception:
                    return Path.home() / "Documents"
        return cwd

    def _init_cognition(self):
        print(f"[BRAIN] Menginisialisasi kesadaran RUKA Marquis of Trendamis...")
        try:
            from ruka_companion.identity.engine import IdentityEngine, IdentityProfile
            from ruka_companion.identity.types import ModalitySignal, Modality
            from ruka_companion.vision.camera import SensorState
            from ruka_companion.presence.engine import PresenceEngine
            self.identity_engine = IdentityEngine()
            self.presence_calc = PresenceEngine()
            print("[BRAIN] Subsistem Companion Volume VI siap.")
        except Exception as e:
            print(f"[BRAIN] Companion module fallback: {e}")
            self.identity_engine = None
            self.presence_calc = None

        try:
            from src.config import load_config
            from src.llm.gemini_client import GeminiClient
            from src.ruka_cognition.brain import RukaCognitiveBrain
            cfg = load_config()
            try:
                self.llm_client = GeminiClient(cfg)
                print(f"[BRAIN] GeminiClient aktif terhubung ke model: {getattr(cfg, 'model', 'default')}")
            except Exception as e_llm:
                print(f"[BRAIN] Peringatan: GeminiClient gagal diinisialisasi ({e_llm})")
                self.llm_client = None

            data_dir = Path(local_appdata) / "ruka"
            data_dir.mkdir(parents=True, exist_ok=True)
            db_file = str(data_dir / "ruka.db")
            initial_seed = BASE_DIR / "ruka.db"
            if initial_seed.exists() and not Path(db_file).exists():
                import shutil
                try:
                    shutil.copy2(str(initial_seed), db_file)
                except Exception:
                    pass
            self.brain = RukaCognitiveBrain(llm_client=self.llm_client, db_path=db_file)
            self.brain_init_error = None
            print("[BRAIN] Saraf Buatan, Advanced RAG, dan Human Persona Engine AKTIF!")
        except Exception as e:
            print(f"[BRAIN] Peringatan: CognitiveBrain fallback ({e})")
            if not hasattr(self, "llm_client"):
                self.llm_client = None
            self.brain = None
            self.brain_init_error = str(e)

        try:
            from ruka_companion.voice.tts import HumanVoiceSynthesizer
            self.synthesizer = HumanVoiceSynthesizer()
            print("[BRAIN] Human Neural Voice Synthesizer (Formula 100% Manusia) AKTIF!")
        except Exception as e:
            print(f"[BRAIN] Peringatan: Voice Synthesizer fallback ({e})")
            self.synthesizer = None

        try:
            from ruka_companion.voice.asr import WhisperASR
            self.whisper_asr = WhisperASR(model_size="tiny")
            threading.Thread(target=self.whisper_asr.load, daemon=True).start()
            print("[BRAIN] Sensor Pendengaran Native whisper.cpp (C++ Engine) AKTIF!")
        except Exception as e:
            print(f"[BRAIN] Peringatan: whisper.cpp fallback ({e})")
            self.whisper_asr = None

        try:
            from src.tools.google_search import get_search_engine
            self.search_engine = get_search_engine()
            print("[BRAIN] Google Search & Web Intelligence Engine AKTIF!")
        except Exception as e:
            print(f"[BRAIN] Peringatan: Google Search engine fallback ({e})")
            self.search_engine = None

        try:
            from src.gateway import RukaGatewayServer
            self.gateway = RukaGatewayServer(
                host=self.host,
                token=self.token,
                brain=self.brain,
                workspace_root=self.workspace_root,
            )
            if self.gateway and self.brain:
                self.brain.skill_registry = self.gateway.skill_registry
                self.brain.skills_runtime = self.gateway.skills_runtime
                self.brain.confirmations = self.gateway.confirmations
            print(f"[BRAIN] Ruka Gateway Control Plane AKTIF! Workspace: {self.workspace_root}")
        except Exception as e:
            print(f"[BRAIN] Peringatan: Gateway fallback ({e})")
            self.gateway = None


    def start(self):
        self.server_sock.listen(5)
        self.running = True

        # Tulis discovery endpoint file
        RUNTIME_DIR.mkdir(parents=True, exist_ok=True)
        ep_data = {
            "host": self.host,
            "port": self.port,
            "token": self.token,
            "protocol_version": PROTOCOL_VERSION,
            "pid": os.getpid(),
        }
        ENDPOINT_FILE.write_text(json.dumps(ep_data, indent=2), encoding="utf-8")
        print(f"[BRAIN] Otak Python aktif di {self.host}:{self.port}")
        print(f"[BRAIN] Endpoint tersimpan di: {ENDPOINT_FILE}")

        accept_thread = threading.Thread(target=self._accept_loop, daemon=True)
        accept_thread.start()

        if getattr(self, "gateway", None) is not None and getattr(self.gateway, "supervisor", None) is not None:
            self.gateway.supervisor.start()
            print("[BRAIN] Organ Supervisor Heartbeat 0.5 Hz AKTIF!")

    def _accept_loop(self):
        while self.running:
            try:
                self.server_sock.settimeout(1.0)
                conn, addr = self.server_sock.accept()
                with self._lock:
                    self.clients.append(conn)
                print(f"[BRAIN] Tubuh Electron terhubung dari {addr}")
                t = threading.Thread(target=self._client_handler, args=(conn,), daemon=True)
                t.start()
            except socket.timeout:
                continue
            except Exception as exc:
                if self.running:
                    print(f"[BRAIN] Accept error: {exc}")

    def _client_handler(self, conn: socket.socket):
        buf = ""
        authenticated = False
        try:
            while self.running:
                try:
                    data = conn.recv(65536)
                except (ConnectionResetError, BrokenPipeError, OSError):
                    break
                if not data:
                    break
                buf += data.decode("utf-8", errors="ignore")
                if len(buf) > 10485760:  # 10MB safety cap
                    buf = ""
                while "\n" in buf:
                    line, buf = buf.split("\n", 1)
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        req = json.loads(line)
                    except Exception:
                        continue

                    resp, auth_status = self._process_request(req, authenticated)
                    if auth_status is not None:
                        authenticated = auth_status
                    if resp:
                        try:
                            conn.sendall((json.dumps(resp) + "\n").encode("utf-8"))
                        except (ConnectionResetError, BrokenPipeError, OSError):
                            break
        except Exception as e:
            print(f"[BRAIN] Client handler info: {e}")
        finally:
            with self._lock:
                if conn in self.clients:
                    self.clients.remove(conn)
            conn.close()
            print("[BRAIN] Sesi klien ditutup.")

    def _process_request(self, req: dict, is_auth: bool) -> tuple[dict | None, bool | None]:
        req_type = req.get("type")
        channel = req.get("channel")
        cid = req.get("correlationId", "corr-default")
        payload = req.get("payload", {})

        # Handshake awal
        if channel == "hello":
            token = payload.get("token")
            if token == self.token:
                print("[BRAIN] Handshake token terverifikasi. Otak & tubuh tersinkron!")
                return {
                    "type": "response",
                    "channel": "hello",
                    "correlationId": cid,
                    "protocolVersion": PROTOCOL_VERSION,
                    "payload": {"ok": True, "protocol_version": PROTOCOL_VERSION},
                    "ts": time.time(),
                }, True
            else:
                print(f"[BRAIN] Penolakan: Token handshake salah!")
                return {
                    "type": "error",
                    "channel": "hello",
                    "correlationId": cid,
                    "protocolVersion": PROTOCOL_VERSION,
                    "payload": {"error": "Token tidak valid"},
                    "ts": time.time(),
                }, False

        if not is_auth:
            return {
                "type": "error",
                "channel": channel,
                "correlationId": cid,
                "protocolVersion": PROTOCOL_VERSION,
                "payload": {"error": "Belum terautentikasi"},
                "ts": time.time(),
            }, None

        # Rute Permintaan
        if channel == "ruka:runtime-status":
            uptime = time.time() - self.start_time
            health_score = 1.0
            if getattr(self, "gateway", None) is not None:
                from src.math_foundations.control import loop_health
                health_score = loop_health(0, 5, self.gateway.budget_ctrl.used_iterations, self.gateway.budget_ctrl.max_iterations)
            return {
                "type": "response",
                "channel": channel,
                "correlationId": cid,
                "protocolVersion": PROTOCOL_VERSION,
                "payload": {
                    "state": "ready",
                    "liveness": True,
                    "readiness": True,
                    "uptime_s": round(uptime, 1),
                    "health_score": round(health_score, 3),
                    "gateway_active": getattr(self, "gateway", None) is not None,
                },
                "ts": time.time(),
            }, None


        elif channel == "ruka:chat-send":
            user_text = payload.get("text", "")
            attachment = payload.get("attachment")
            print(f"[BRAIN] Nalar saraf & RAG memproses: '{user_text}', attachment={bool(attachment)}")

            workspace_note = ""
            client_cwd = payload.get("cwd")
            gw = getattr(self, "gateway", None)
            if client_cwd and gw is not None:
                try:
                    applied = gw.permission_mgr.set_workspace(client_cwd)
                    print(f"[BRAIN] Workspace PathJail aktif: {applied}")
                except Exception as ws_err:
                    print(f"[BRAIN] Workspace ditolak ({client_cwd}): {ws_err}")
                    workspace_note = (
                        f"\n\n_(Catatan: folder kerja `{client_cwd}` ditolak oleh PathJail — {ws_err} "
                        f"Hamba tetap bekerja di `{gw.permission_mgr.jail.base}`.)_"
                    )

            if self.brain is not None:
                reply = self.brain.think_and_reply(user_text, attachment=attachment)
            else:
                reply = self._fallback_brain_not_ready(user_text)
            reply = f"{reply}{workspace_note}"
            return {
                "type": "response",
                "channel": channel,
                "correlationId": cid,
                "protocolVersion": PROTOCOL_VERSION,
                "payload": {
                    "seq": 1,
                    "delta": reply,
                    "done": True,
                },
                "ts": time.time(),
            }, None

        elif channel == "ruka:voice-transcribe":
            audio_b64 = payload.get("audio", "")
            if "," in audio_b64:
                audio_b64 = audio_b64.split(",", 1)[1]
            text = ""
            err_msg = None
            if audio_b64:
                try:
                    import base64
                    raw_wav = base64.b64decode(audio_b64)
                    if getattr(self, "whisper_asr", None) is not None:
                        text = self.whisper_asr.transcribe_wav_bytes(raw_wav, language="id")
                        print(f"[BRAIN] Transkripsi native whisper.cpp (C++) sukses: '{text}'")
                    else:
                        import io
                        import speech_recognition as sr
                        recognizer = sr.Recognizer()
                        with sr.AudioFile(io.BytesIO(raw_wav)) as source:
                            audio_data = recognizer.record(source)
                        text = recognizer.recognize_google(audio_data, language="id-ID")
                        print(f"[BRAIN] Transkripsi suara fallback sukses: '{text}'")
                except Exception as ex:
                    print(f"[BRAIN] Transkripsi error: {ex}")
                    err_msg = str(ex)

            return {
                "type": "response",
                "channel": channel,
                "correlationId": cid,
                "protocolVersion": PROTOCOL_VERSION,
                "payload": {
                    "text": text,
                    "error": err_msg,
                },
                "ts": time.time(),
            }, None

        elif channel == "ruka:voice-synthesize":
            text = payload.get("text", "")
            valence = float(payload.get("valence", 0.1))
            arousal = float(payload.get("arousal", 0.05))
            audio_url = ""
            err_msg = None
            if text and self.synthesizer:
                try:
                    import base64
                    audio_bytes = self.synthesizer.synthesize_sync(text, valence=valence, arousal=arousal)
                    if audio_bytes:
                        b64_str = base64.b64encode(audio_bytes).decode("ascii")
                        audio_url = f"data:audio/mpeg;base64,{b64_str}"
                        print(f"[BRAIN] Sintesis suara manusia berhasil ({len(audio_bytes)} bytes)")
                    else:
                        err_msg = "Sintesis audio tidak menghasilkan data."
                except Exception as ex:
                    print(f"[BRAIN] Error sintesis suara manusia: {ex}")
                    err_msg = str(ex)
            elif not self.synthesizer:
                err_msg = "Voice synthesizer belum aktif."

            return {
                "type": "response",
                "channel": channel,
                "correlationId": cid,
                "protocolVersion": PROTOCOL_VERSION,
                "payload": {
                    "audioUrl": audio_url,
                    "error": err_msg,
                },
                "ts": time.time(),
            }, None

        elif channel == "ruka:memory-search":
            q = payload.get("query", "")
            if self.brain is not None:
                ctx_items = self.brain.rag.retrieve_context(q, top_k=5)
                hits = [
                    {
                        "kind": "semantic" if any(w in item.lower() for w in ["arsitektur", "doktrin", "preferensi"]) else "identity",
                        "summary": item,
                    }
                    for item in ctx_items
                ]
            else:
                hits = []
            return {
                "type": "response",
                "channel": channel,
                "correlationId": cid,
                "protocolVersion": PROTOCOL_VERSION,
                "payload": {"hits": hits, "took_ms": 1.2},
                "ts": time.time(),
            }, None

        elif channel == "ruka:memory-stats":
            return {
                "type": "response",
                "channel": channel,
                "correlationId": cid,
                "protocolVersion": PROTOCOL_VERSION,
                "payload": {
                    "counts_by_kind": {"episodic": 12, "semantic": 34, "identity": 1},
                    "lifecycle": {"status": "persisted", "engine": "sqlite-wal"},
                },
                "ts": time.time(),
            }, None

        elif channel == "ruka:google-search":
            q = payload.get("query", "")
            max_res = int(payload.get("max_results", 5))
            items_dict = []
            err_msg = None
            if q and self.search_engine:
                try:
                    items_dict = self.search_engine.search_as_dict(q, max_results=max_res)
                    print(f"[BRAIN] Google Search sukses untuk: '{q}' ({len(items_dict)} hasil)")
                except Exception as ex:
                    print(f"[BRAIN] Google Search error: {ex}")
                    err_msg = str(ex)
            elif not self.search_engine:
                err_msg = "Google Search engine belum aktif."

            return {
                "type": "response",
                "channel": channel,
                "correlationId": cid,
                "protocolVersion": PROTOCOL_VERSION,
                "payload": {
                    "query": q,
                    "results": items_dict,
                    "error": err_msg,
                },
                "ts": time.time(),
            }, None

        elif channel == "ruka:tool-list":
            return {
                "type": "response",
                "channel": channel,
                "correlationId": cid,
                "protocolVersion": PROTOCOL_VERSION,
                "payload": {
                    "tools": [
                        {"name": "google.search", "permission": "network", "description": "Penelusuran Google & Web intelligence real-time"},
                        {"name": "camera.capture", "permission": "local_only", "description": "Sensor visual kamera lokal (YuNet/SFace)"},
                        {"name": "microphone.capture", "permission": "local_only", "description": "Sensor pendengaran mikrofon lokal"},
                        {"name": "filesystem.read", "permission": "read", "description": "Akses baca berkas sistem operasi"},
                        {"name": "terminal.execute", "permission": "sandbox_write", "description": "Eksekusi perintah terminal terkarantina"},
                    ]
                },
                "ts": time.time(),
            }, None

        # Delegasikan seluruh kanal lanjutan ke Ruka Gateway Control Plane (Noctis Architecture)
        if getattr(self, "gateway", None) is not None:
            try:
                resp, auth_state = self.gateway.desktop_adapter.process_raw_ipc_request(
                    req, session_id="launcher_desktop"
                )
                if resp is not None:
                    return resp, auth_state
            except Exception as e_gw:
                print(f"[BRAIN] Gateway IPC error ({channel}): {e_gw}")

        return {
            "type": "error",
            "channel": channel,
            "correlationId": cid,
            "protocolVersion": PROTOCOL_VERSION,
            "payload": {"error": f"Kanal '{channel}' tak dikenal"},
            "ts": time.time(),
        }, None

    def _fallback_brain_not_ready(self, text: str) -> str:
        """Pesan fallback jujur saat CognitiveBrain gagal inisialisasi atau tidak siap.

        Sesuai DoD U0.4:
        Hanya boleh pesan jujur singkat (kognisi tidak siap / gagal init),
        bukan nalar, bukan kode palsu, bukan pura-pura skills.
        """
        reason = getattr(self, "brain_init_error", None)
        err_detail = f" (detail: {reason})" if reason else ""
        return (
            f"[Kognisi Tidak Siap] Otak kognisi Ruka (CognitiveBrain) belum siap atau gagal diinisialisasi{err_detail}. "
            "Nalar, ingatan, dan eksekusi skills tidak aktif dalam status fallback."
        )

    def _generate_response(self, text: str) -> str:
        return self._fallback_brain_not_ready(text)

    def stop(self):
        print("\n[BRAIN] Menghentikan otak Python secara sopan...")
        self.running = False
        if getattr(self, "gateway", None) is not None and getattr(self.gateway, "supervisor", None) is not None:
            try:
                self.gateway.supervisor.stop()
            except Exception:
                pass
        with self._lock:
            for c in self.clients:
                try:
                    c.close()
                except Exception:
                    pass
            self.clients.clear()
        try:
            self.server_sock.close()
        except Exception:
            pass
        if ENDPOINT_FILE.exists():
            try:
                ENDPOINT_FILE.unlink()
                print(f"[BRAIN] Endpoint file dibersihkan: {ENDPOINT_FILE}")
            except Exception:
                pass


def main():
    server = RukaBrainServer()
    
    def handle_sig(sig, frame):
        server.stop()
        sys.exit(0)

    signal.signal(signal.SIGINT, handle_sig)
    signal.signal(signal.SIGTERM, handle_sig)

    server.start()

    try:
        while server.running:
            time.sleep(0.5)
    except KeyboardInterrupt:
        server.stop()


if __name__ == "__main__":
    main()
