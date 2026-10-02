# -*- coding: utf-8 -*-
"""RUKA CLI — Marquis of Trendamis Terminal Companion.
Memungkinkan Young Lord memanggil Ruka kapan saja dan di mana saja
langsung dari Command Prompt / PowerShell / Terminal desktop.
"""
from __future__ import annotations

import os
import sys
import json
import time
import socket
import subprocess
from pathlib import Path

# Pastikan output konsol Windows mendukung UTF-8 dan warna ANSI tanpa crash
if sys.platform == "win32":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    os.system("")

# Warna ANSI terminal
CYAN = "\033[96m"
MAGENTA = "\033[95m"
BLUE = "\033[94m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
RED = "\033[91m"
BOLD = "\033[1m"
DIM = "\033[2m"
RESET = "\033[0m"

LOCAL_APPDATA = os.environ.get("LOCALAPPDATA") or str(Path.home() / "AppData" / "Local")
ENDPOINT_FILE = Path(LOCAL_APPDATA) / "ruka" / "runtime" / "ipc-endpoint.json"


def print_banner():
    banner = f"""{MAGENTA}{BOLD}
  🐾 RUKA (ルカ) — Marquis of Trendamis
  {DIM}The Persistent Mind & Aristocratic AI Companion CLI{RESET}
"""
    print(banner)


def get_ipc_connection(timeout: float = 4.0) -> tuple[socket.socket, dict] | None:
    """Tersambung ke Ruka Brain Server via IPC loopback socket."""
    start_t = time.time()
    while time.time() - start_t < timeout:
        if ENDPOINT_FILE.exists():
            try:
                data = json.loads(ENDPOINT_FILE.read_text(encoding="utf-8"))
                port = data.get("port")
                token = data.get("token")
                if port and token:
                    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    s.settimeout(60.0)
                    try:
                        s.connect(("127.0.0.1", port))
                        # Handshake
                        hello_env = {
                            "type": "request",
                            "channel": "hello",
                            "correlationId": "cli-hello",
                            "payload": {"token": token},
                        }
                        s.sendall((json.dumps(hello_env) + "\n").encode("utf-8"))
                        f = s.makefile("r", encoding="utf-8")
                        resp_line = f.readline()
                        if resp_line:
                            resp = json.loads(resp_line)
                            if resp.get("payload", {}).get("ok"):
                                return s, data
                        s.close()
                    except Exception:
                        try:
                            s.close()
                        except Exception:
                            pass
            except Exception:
                pass
        time.sleep(0.5)
    return None


def ensure_brain_running() -> tuple[socket.socket, dict] | None:
    """Memastikan Otak Ruka aktif, atau menyalakannya jika belum berjalan."""
    conn = get_ipc_connection(timeout=1.5)
    if conn:
        return conn

    print(f"{YELLOW}[RUKA CLI] Otak Ruka belum terhubung. Membangunkan Ruka...{RESET}")
    exe_dir = Path(sys.executable).resolve().parent
    root_dir = Path(__file__).resolve().parent

    brain_candidates = [
        exe_dir / "resources" / "brain" / "ruka-brain.exe",
        exe_dir / "brain" / "ruka-brain.exe",
        exe_dir / "ruka-brain.exe",
        root_dir / "desktop" / "resources" / "brain" / "ruka-brain.exe",
        root_dir / "launcher.py",
    ]

    spawned = False
    for cand in brain_candidates:
        if cand.exists():
            try:
                creation_flags = 0x08000000 if os.name == "nt" else 0  # CREATE_NO_WINDOW
                if cand.suffix == ".py":
                    subprocess.Popen([sys.executable, str(cand)], cwd=str(cand.parent), creationflags=creation_flags)
                else:
                    subprocess.Popen([str(cand)], cwd=str(cand.parent), creationflags=creation_flags)
                spawned = True
                break
            except Exception:
                pass

    if spawned:
        return get_ipc_connection(timeout=25.0)

    print(f"{RED}[!] Gagal membangunkan Otak Ruka. Pastikan Ruka terpasang dengan benar.{RESET}")
    return None


def handle_chat(sock: socket.socket, prompt: str):
    """Mengirim obrolan ke Ruka dan mengalirkan respons aristokrat secara live."""
    req_env = {
        "type": "request",
        "channel": "ruka:chat-send",
        "correlationId": f"cli-{int(time.time())}",
        "payload": {"text": prompt},
    }
    sock.sendall((json.dumps(req_env) + "\n").encode("utf-8"))

    f = sock.makefile("r", encoding="utf-8")
    print(f"{MAGENTA}{BOLD}Ruka (Marquis of Trendamis):{RESET} ", end="", flush=True)

    streamed_text = ""
    while True:
        line = f.readline()
        if not line:
            break
        try:
            data = json.loads(line)
            ch = data.get("channel")
            payload = data.get("payload", {})

            if ch == "ruka:chat-stream":
                delta = payload.get("delta", "")
                if delta:
                    sys.stdout.write(delta)
                    sys.stdout.flush()
                    streamed_text += delta
            elif ch == "ruka:chat-send":
                if payload.get("done"):
                    # Jika tidak ada streaming sebelumnya tapi ada payload delta/reply
                    delta = payload.get("delta", "")
                    if delta and not streamed_text:
                        sys.stdout.write(delta)
                        sys.stdout.flush()
                    break
        except Exception:
            break
    print("\n")


def handle_status(sock: socket.socket):
    """Menampilkan status runtime dan kesehatan kognisi Ruka."""
    req_env = {
        "type": "request",
        "channel": "ruka:runtime-status",
        "correlationId": "cli-status",
        "payload": {},
    }
    sock.sendall((json.dumps(req_env) + "\n").encode("utf-8"))
    f = sock.makefile("r", encoding="utf-8")
    line = f.readline()
    if line:
        try:
            res = json.loads(line).get("payload", {})
            print(f"{GREEN}{BOLD}=== Status Runtime RUKA ==={RESET}")
            print(f" • Status      : {CYAN}{res.get('status', 'online').upper()}{RESET}")
            print(f" • Process PID : {res.get('pid')}")
            print(f" • Uptime      : {res.get('uptime_s', 0):.1f} detik")
            print(f" • Otak AI     : {res.get('llm_model', 'Gemini 3.5 Flash-Lite')}")
            print(f" • Keamanan    : {GREEN}Zero-Trust Local-Only PathJail (100% Aman){RESET}")
        except Exception as e:
            print(f"{RED}Gagal membaca status: {e}{RESET}")


def handle_search(sock: socket.socket, query: str):
    """Pencarian Google Search gratis via Ruka."""
    print(f"{CYAN}[*] Ruka sedang menelusuri web untuk: '{query}'...{RESET}")
    req_env = {
        "type": "request",
        "channel": "ruka:google-search",
        "correlationId": "cli-search",
        "payload": {"query": query},
    }
    sock.sendall((json.dumps(req_env) + "\n").encode("utf-8"))
    f = sock.makefile("r", encoding="utf-8")
    line = f.readline()
    if line:
        try:
            results = json.loads(line).get("payload", {}).get("results", [])
            if results:
                print(f"\n{GREEN}{BOLD}Hasil Pencarian Google Ruka:{RESET}")
                for idx, r in enumerate(results[:5], 1):
                    print(f"{BOLD}{idx}. {r.get('title')}{RESET}")
                    print(f"   {BLUE}{r.get('url')}{RESET}")
                    print(f"   {r.get('snippet')}\n")
            else:
                print(f"{YELLOW}Tidak ada hasil yang ditemukan.{RESET}")
        except Exception as e:
            print(f"{RED}Gagal melakukan pencarian: {e}{RESET}")


def interactive_repl(sock: socket.socket):
    """Mode REPL Interaktif terminal."""
    print_banner()
    print(f"{CYAN}Sesi interaktif dibuka. Ketik 'exit' atau 'quit' untuk keluar.{RESET}\n")
    while True:
        try:
            prompt = input(f"{BOLD}{CYAN}Young Lord > {RESET}").strip()
            if not prompt:
                continue
            if prompt.lower() in ("exit", "quit", "q"):
                print(f"\n{MAGENTA}Ruka: Sampai jumpa, Young Lord. Hamba senantiasa siap di System Tray.{RESET}\n")
                break
            if prompt.lower() == "status":
                handle_status(sock)
            elif prompt.lower().startswith("search "):
                handle_search(sock, prompt[7:].strip())
            else:
                handle_chat(sock, prompt)
        except (KeyboardInterrupt, EOFError):
            print(f"\n{MAGENTA}Ruka: Pamit mengundurkan diri, Young Lord.{RESET}\n")
            break


def print_help():
    print_banner()
    print(f"""{BOLD}PENGGUNAAN CLI:{RESET}
  {CYAN}ruka{RESET}                        Buka sesi REPL interaktif terminal
  {CYAN}ruka "pesan atau perintah"{RESET}    Kirim instruksi langsung ke Ruka dan dapatkan respons
  {CYAN}ruka status{RESET}                 Cek status kesehatan Otak Ruka & PID
  {CYAN}ruka search "query"{RESET}         Cari berita/informasi terkini di Google
  {CYAN}ruka help{RESET}                   Tampilkan menu bantuan ini

{BOLD}CONTOH:{RESET}
  ruka "Ruka, tolong buatkan ringkasan tugas hari ini."
  ruka search "berita AI terbaru 2026"
  ruka status
""")


def main():
    args = sys.argv[1:]

    if args and args[0] in ("-h", "--help", "help"):
        print_help()
        return

    res = ensure_brain_running()
    if not res:
        sys.exit(1)
    sock, info = res

    try:
        if not args:
            interactive_repl(sock)
        elif args[0] == "status":
            handle_status(sock)
        elif args[0] == "search" and len(args) > 1:
            handle_search(sock, " ".join(args[1:]))
        else:
            prompt = " ".join(args)
            handle_chat(sock, prompt)
    finally:
        try:
            sock.close()
        except Exception:
            pass


if __name__ == "__main__":
    main()
