# -*- coding: utf-8 -*-
"""RUKA CLI — Marquis of Trendamis Terminal Companion & Coding Agent.
Memungkinkan Young Lord memanggil Ruka kapan saja dan di mana saja
langsung dari Command Prompt / PowerShell / Terminal desktop.
Mendukung obrolan kognitif, evaluasi kode, review, git diff, dan eksekusi agentic.
"""
from __future__ import annotations

import json
import os
import re
import socket
import subprocess
import sys
import time
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
WHITE = "\033[97m"
BOLD = "\033[1m"
DIM = "\033[2m"
RESET = "\033[0m"

LOCAL_APPDATA = os.environ.get("LOCALAPPDATA") or str(Path.home() / "AppData" / "Local")
ENDPOINT_FILE = Path(LOCAL_APPDATA) / "ruka" / "runtime" / "ipc-endpoint.json"


def print_banner():
    banner = f"""{MAGENTA}{BOLD}
  🐾 RUKA (ルカ) — Marquis of Trendamis
  {DIM}The Persistent Mind & Aristocratic Coding Agent CLI{RESET}
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


def render_formatted_output(text: str):
    """Menampilkan teks respons dengan blok kode terpisah rapi (Lore Lock rendering)."""
    # Memisahkan markdown fenced code blocks
    parts = re.split(r"(```[a-zA-Z0-9_-]*\n[\s\S]*?\n```)", text)
    for part in parts:
        if part.startswith("```"):
            lines = part.splitlines()
            lang = lines[0].replace("```", "").strip() or "code"
            code_body = "\n".join(lines[1:-1])
            print(f"\n{CYAN}┌── [{lang.upper()}] ───────────────────────────────────────┐{RESET}")
            for cline in code_body.splitlines():
                print(f"{WHITE}│  {cline}{RESET}")
            print(f"{CYAN}└── 100% Pure Code Block ─────────────────────────────┘{RESET}\n")
        else:
            if part.strip():
                print(part.strip())


def handle_chat(sock: socket.socket, prompt: str):
    """Mengirim obrolan ke Ruka dan mengalirkan respons aristokrat secara live."""
    raw_cwd = os.environ.get("PWD") or os.getcwd()
    if os.name == "nt" and re.match(r"^/[a-zA-Z]/", raw_cwd):
        raw_cwd = re.sub(r"^/([a-zA-Z])/", r"\1:/", raw_cwd)
    req_env = {
        "type": "request",
        "channel": "ruka:chat-send",
        "correlationId": f"cli-{int(time.time())}",
        "payload": {"text": prompt, "cwd": raw_cwd},
    }
    sock.sendall((json.dumps(req_env) + "\n").encode("utf-8"))

    f = sock.makefile("r", encoding="utf-8")
    print(f"\n{MAGENTA}{BOLD}Ruka (Marquis of Trendamis):{RESET}\n")

    full_text = ""
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
                    full_text += delta
            elif ch == "ruka:chat-send":
                delta = payload.get("delta", "")
                if delta and not full_text:
                    full_text = delta
                if payload.get("done"):
                    break
        except Exception:
            break

    if full_text:
        render_formatted_output(full_text)
    print()


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
            print(f"\n{GREEN}{BOLD}=== Status Runtime RUKA Coding Agent ==={RESET}")
            print(f" • Status        : {CYAN}{res.get('status', 'online').upper()}{RESET}")
            print(f" • Process PID   : {res.get('pid')}")
            print(f" • Uptime        : {res.get('uptime_s', 0):.1f} detik")
            print(f" • Otak Kognisi  : {res.get('llm_model', 'Gemini 3.5 Flash-Lite')}")
            print(f" • Coding Engine : {MAGENTA}Claude Code Parity v1.0 (Phase 1–3 Ready){RESET}")
            print(f" • Sandbox       : {GREEN}Zero-Trust PathJail & CodeEvaluator Active{RESET}\n")
        except Exception as e:
            print(f"{RED}Gagal membaca status: {e}{RESET}")


def handle_diff(target_file: str | None = None):
    """Menampilkan git diff berwarna di terminal dengan format aristokrat."""
    cmd = ["git", "diff"]
    if target_file:
        cmd.extend(["--", target_file])

    try:
        proc = subprocess.run(cmd, capture_output=True, text=True)
        if proc.returncode != 0:
            print(f"{RED}Gagal membaca git diff: {proc.stderr.strip()}{RESET}")
            return

        diff_text = proc.stdout
        if not diff_text.strip():
            print(f"{GREEN}[✓] Working tree bersih, tidak ada perbedaan git.{RESET}")
            return

        print(f"\n{CYAN}{BOLD}=== Git Diff (Perubahan Terkini) ==={RESET}\n")
        for line in diff_text.splitlines():
            if line.startswith("+++") or line.startswith("---"):
                print(f"{BOLD}{line}{RESET}")
            elif line.startswith("+"):
                print(f"{GREEN}{line}{RESET}")
            elif line.startswith("-"):
                print(f"{RED}{line}{RESET}")
            elif line.startswith("@@"):
                print(f"{CYAN}{line}{RESET}")
            else:
                print(f"{DIM}{line}{RESET}")
        print()
    except Exception as e:
        print(f"{RED}Error saat menjalankan git diff: {e}{RESET}")


def handle_git_status():
    """Menampilkan git status secara ringkas dan rapi."""
    try:
        proc = subprocess.run(["git", "status", "--porcelain=v1", "-uall"], capture_output=True, text=True)
        branch_proc = subprocess.run(["git", "branch", "--show-current"], capture_output=True, text=True)
        branch = branch_proc.stdout.strip() or "HEAD"

        print(f"\n{CYAN}{BOLD}=== Git Status: Branch {branch} ==={RESET}")
        lines = proc.stdout.splitlines()
        if not lines:
            print(f"{GREEN}  [✓] Working directory bersih (clean). Tidak ada perubahan.{RESET}\n")
            return

        for line in lines:
            if len(line) < 3:
                continue
            x, y = line[0], line[1]
            fname = line[3:].strip()
            if x == "?" and y == "?":
                print(f"  {MAGENTA}[Untracked]{RESET} {fname}")
            elif x in ("M", "A", "D", "R", "C"):
                print(f"  {GREEN}[Staged]   {RESET} {fname} ({x})")
            elif y in ("M", "D"):
                print(f"  {YELLOW}[Modified] {RESET} {fname} ({y})")
        print()
    except Exception as e:
        print(f"{RED}Error git status: {e}{RESET}")


def handle_review(sock: socket.socket, target_path: str):
    """Menjalankan code review pada berkas/folder yang ditentukan."""
    p = Path(target_path)
    if not p.exists():
        print(f"{RED}[!] Path target tidak ditemukan: {target_path}{RESET}")
        return

    content_preview = ""
    if p.is_file():
        try:
            content_preview = p.read_text(encoding="utf-8", errors="replace")[:10000]
        except Exception:
            pass

    prompt = (
        f"Young Lord menugaskan untuk melakukan review mendalam pada berkas: '{target_path}'.\n"
        f"Berikut isi berkas:\n```\n{content_preview}\n```\n"
        "Analisis dengan saksama: potensi bug, arsitektur, efisiensi waktu dan memori, serta standar keamanan koding."
    )
    handle_chat(sock, prompt)


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
    """Mode REPL Interaktif terminal dengan dukungan command koding."""
    print_banner()
    print(f"{CYAN}Sesi interaktif koding dibuka. Ketik 'help' untuk daftar perintah atau 'exit' untuk keluar.{RESET}\n")
    while True:
        try:
            prompt = input(f"{BOLD}{CYAN}Young Lord > {RESET}").strip()
            if not prompt:
                continue
            if prompt.lower() in ("exit", "quit", "q"):
                print(f"\n{MAGENTA}Ruka: Sampai jumpa, Young Lord. Hamba senantiasa siap sedia mendampingi Anda.{RESET}\n")
                break
            if prompt.lower() == "status":
                handle_status(sock)
            elif prompt.lower() == "diff":
                handle_diff()
            elif prompt.lower() in ("git-status", "gs"):
                handle_git_status()
            elif prompt.lower().startswith("review "):
                handle_review(sock, prompt[7:].strip())
            elif prompt.lower().startswith("search "):
                handle_search(sock, prompt[7:].strip())
            else:
                handle_chat(sock, prompt)
        except (KeyboardInterrupt, EOFError):
            print(f"\n{MAGENTA}Ruka: Pamit mengundurkan diri, Young Lord.{RESET}\n")
            break


def print_help():
    print_banner()
    print(f"""{BOLD}PENGGUNAAN CLI RUKA CODING AGENT:{RESET}
  {CYAN}ruka{RESET}                        Buka sesi REPL interaktif terminal
  {CYAN}ruka "pesan / perintah"{RESET}    Kirim instruksi coding/tugas ke Ruka
  {CYAN}ruka review <path>{RESET}          Review berkas/kode dengan analisis mendalam
  {CYAN}ruka diff [path]{RESET}            Tampilkan perbedaan kode git diff berwarna
  {CYAN}ruka git-status{RESET}             Periksa ringkasan status git repositori
  {CYAN}ruka status{RESET}                 Cek kesehatan runtime Otak Ruka & PID
  {CYAN}ruka search "query"{RESET}         Cari berita/informasi terkini di Google
  {CYAN}ruka help{RESET}                   Tampilkan bantuan ini

{BOLD}CONTOH CODING:{RESET}
  ruka "Perbaiki race condition di modul auth.py"
  ruka review src/agent/orchestrator.py
  ruka diff
  ruka "Implementasikan fitur rate limiter dengan token bucket"
""")


def main():
    args = sys.argv[1:]

    if args and args[0] in ("-h", "--help", "help"):
        print_help()
        return

    if args and args[0] == "diff":
        handle_diff(args[1] if len(args) > 1 else None)
        return

    if args and args[0] in ("git-status", "gs"):
        handle_git_status()
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
        elif args[0] == "review" and len(args) > 1:
            handle_review(sock, args[1])
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
