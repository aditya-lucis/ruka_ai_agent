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
import threading
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


class TerminalSpinner:
    """Animasi spinner nokturnal aristokrat yang elegan saat Ruka sedang berpikir/bekerja."""

    def __init__(self, message: str = "Marquis sedang menelaah ruang kerja & merajut nalar..."):
        self.message = message
        self.running = False
        self._thread: threading.Thread | None = None

    def _spin(self):
        frames = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]
        idx = 0
        while self.running:
            frame = frames[idx % len(frames)]
            sys.stdout.write(f"\r  {MAGENTA}{frame}{RESET} {DIM}{self.message}{RESET} ")
            sys.stdout.flush()
            time.sleep(0.08)
            idx += 1
        # Bersihkan baris spinner
        sys.stdout.write("\r\033[K")
        sys.stdout.flush()

    def start(self):
        self.running = True
        self._thread = threading.Thread(target=self._spin, daemon=True)
        self._thread.start()

    def stop(self):
        self.running = False
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=0.3)
        sys.stdout.write("\r\033[K")
        sys.stdout.flush()


def get_git_info() -> str:
    """Mendeteksi branch git aktif dan kebersihan status repositori."""
    try:
        branch = subprocess.check_output(
            ["git", "branch", "--show-current"],
            stderr=subprocess.DEVNULL,
            text=True,
        ).strip()
        if not branch:
            branch = subprocess.check_output(
                ["git", "rev-parse", "--abbrev-ref", "HEAD"],
                stderr=subprocess.DEVNULL,
                text=True,
            ).strip()
        status = subprocess.check_output(
            ["git", "status", "--porcelain=v1"],
            stderr=subprocess.DEVNULL,
            text=True,
        ).strip()
        clean = f"{GREEN}clean{RESET}" if not status else f"{YELLOW}modified{RESET}"
        return f"{CYAN}{branch}{RESET} [{clean}]"
    except Exception:
        return f"{DIM}non-git workspace{RESET}"


def print_banner():
    raw_cwd = os.environ.get("PWD") or os.getcwd()
    if os.name == "nt" and re.match(r"^/[a-zA-Z]/", raw_cwd):
        raw_cwd = re.sub(r"^/([a-zA-Z])/", r"\1:/", raw_cwd)
    git_info = get_git_info()

    banner = f"""
{MAGENTA}{BOLD}╭─────────────────────────────────────────────────────────────────────────────╮
│ 🐾 RUKA (ルカ) — Marquis of Trendamis · Aristocratic Coding Agent v0.3.1    │
├─────────────────────────────────────────────────────────────────────────────┤{RESET}
  {BOLD}📂 Workspace{RESET} : {CYAN}{raw_cwd}{RESET}
  {BOLD}🌿 Git State{RESET} : {git_info}
  {BOLD}🧠 Mind Core{RESET} : {MAGENTA}Gemini 3.5 Flash-Lite & Multi-Turn Cognitive Brain{RESET}
  {BOLD}🛡️  Security{RESET}  : {GREEN}Zero-Trust PathJail & CodeEvaluator Active{RESET}
{MAGENTA}{BOLD}╰─────────────────────────────────────────────────────────────────────────────╯{RESET}
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
                    s.settimeout(300.0)
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


def handle_chat(sock: socket.socket, prompt: str, inline_confirm: bool = True, attachment: dict | None = None) -> bool:
    """Mengirim obrolan ke Ruka dan mengalirkan respons aristokrat secara live dengan spinner & inline approval."""
    raw_cwd = os.environ.get("PWD") or os.getcwd()
    if os.name == "nt" and re.match(r"^/[a-zA-Z]/", raw_cwd):
        raw_cwd = re.sub(r"^/([a-zA-Z])/", r"\1:/", raw_cwd)
    payload_data = {"text": prompt, "cwd": raw_cwd}
    if attachment:
        payload_data["attachment"] = attachment

    req_env = {
        "type": "request",
        "channel": "ruka:chat-send",
        "correlationId": f"cli-{int(time.time())}",
        "payload": payload_data,
    }

    spinner = TerminalSpinner("Marquis sedang menelaah ruang kerja & merajut nalar...")
    spinner.start()
    f = sock.makefile("r", encoding="utf-8")

    full_text = ""
    try:
        sock.sendall((json.dumps(req_env) + "\n").encode("utf-8"))
        first_line = True
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
                        if first_line:
                            spinner.stop()
                            print(f"\n{MAGENTA}{BOLD}Ruka (Marquis of Trendamis):{RESET}\n")
                            first_line = False
                        full_text += delta
                elif ch == "ruka:chat-send":
                    delta = payload.get("delta", "")
                    if delta and not full_text:
                        full_text = delta
                    if payload.get("done"):
                        break
            except Exception:
                break
    except (socket.timeout, TimeoutError):
        spinner.stop()
        print(f"\n{YELLOW}⚠️  Waktu tunggu nalar terlampaui (Timeout), Young Lord.{RESET}")
        print(f"{DIM}Nalar Marquis atau perancangan berkas kode yang masif memerlukan waktu lebih dari 300 detik.{RESET}")
        print(f"{DIM}Koneksi IPC akan disegarkan secara otomatis agar Anda dapat melanjutkan sesi.{RESET}\n")
        return False
    except (ConnectionError, OSError) as conn_err:
        spinner.stop()
        print(f"\n{RED}⚠️  Koneksi ke Otak Ruka terputus: {conn_err}{RESET}\n")
        return False
    finally:
        spinner.stop()

    if full_text:
        render_formatted_output(full_text)
    print()

    # Inline Interactive Confirmation Gate (Claude Code caliber)
    needs_approval = (
        "Titah menunggu restu Young Lord" in full_text
        or "Aksi Menunggu Persetujuan" in full_text
        or bool(re.search(r"ID `[a-f0-9]+`\s*·\s*risiko", full_text, re.IGNORECASE))
    )
    if inline_confirm and needs_approval:
        try:
            confirm = input(f"{BOLD}{YELLOW}  [?] Restui eksekusi tindakan di atas sekarang? [Y/n]: {RESET}").strip().lower()
            if confirm in ("", "y", "ya", "yes"):
                print(f"{GREEN}  [✓] Titah direstui oleh Young Lord. Mengeksekusi...{RESET}\n")
                return handle_chat(sock, "ya", inline_confirm=False)
            else:
                print(f"{RED}  [✕] Titah dibatalkan oleh Young Lord.{RESET}\n")
                return handle_chat(sock, "batal", inline_confirm=False)
        except (KeyboardInterrupt, EOFError):
            pass
    return True


def handle_status(sock: socket.socket):
    """Menampilkan status runtime dan kesehatan kognisi Ruka."""
    spinner = TerminalSpinner("Mengambil status kesehatan runtime Ruka...")
    spinner.start()
    try:
        req_env = {
            "type": "request",
            "channel": "ruka:runtime-status",
            "correlationId": "cli-status",
            "payload": {},
        }
        sock.sendall((json.dumps(req_env) + "\n").encode("utf-8"))
        f = sock.makefile("r", encoding="utf-8")
        line = f.readline()
    finally:
        spinner.stop()

    if line:
        try:
            res = json.loads(line).get("payload", {})
            print(f"\n{GREEN}{BOLD}=== Status Runtime RUKA Coding Agent ==={RESET}")
            print(f" • Status        : {CYAN}{res.get('state', 'ready').upper()}{RESET}")
            print(f" • Health Score : {GREEN}{res.get('health_score', 1.0) * 100:.1f}%{RESET}")
            print(f" • Uptime        : {res.get('uptime_s', 0):.1f} detik")
            print(f" • Gateway       : {CYAN}{'Active (Zero-Trust)' if res.get('gateway_active') else 'Inactive'}{RESET}")
            print(f" • Coding Engine : {MAGENTA}Claude Code Parity v2.0 (LLM ReAct Loop Active){RESET}")
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


def build_image_attachment(img_path: str) -> dict | None:
    """Membaca berkas citra visual dan mengonversinya menjadi payload multimodal."""
    p = Path(img_path)
    if not p.exists() or not p.is_file():
        print(f"{RED}[!] Berkas gambar tidak ditemukan: {img_path}{RESET}")
        return None
    try:
        import base64
        import mimetypes
        mime, _ = mimetypes.guess_type(str(p))
        mime = mime or "image/png"
        raw_b64 = base64.b64encode(p.read_bytes()).decode("ascii")
        return {
            "isImage": True,
            "type": "image",
            "name": p.name,
            "mime_type": mime,
            "data": raw_b64,
        }
    except Exception as e:
        print(f"{RED}[!] Gagal membaca berkas gambar: {e}{RESET}")
        return None


def handle_search(sock: socket.socket, query: str):
    """Pencarian Google Search gratis via Ruka."""
    spinner = TerminalSpinner(f"Ruka sedang menelusuri web untuk: '{query}'...")
    spinner.start()
    try:
        req_env = {
            "type": "request",
            "channel": "ruka:google-search",
            "correlationId": "cli-search",
            "payload": {"query": query},
        }
        sock.sendall((json.dumps(req_env) + "\n").encode("utf-8"))
        f = sock.makefile("r", encoding="utf-8")
        line = f.readline()
    finally:
        spinner.stop()

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
    """Mode REPL Interaktif terminal dengan estetika dan responsivitas setara Claude Code."""
    print_banner()
    print(f"{DIM}Ketik perintah coding, '/help' untuk bantuan, atau '/clear' untuk menyegarkan layar.{RESET}\n")
    while True:
        try:
            prompt = input(f"{BOLD}{CYAN}Young Lord{RESET} {DIM}›{RESET} ").strip()
            if not prompt:
                continue
            if prompt.lower() in ("exit", "quit", "q", "/exit", "/quit", "/q"):
                print(f"\n{MAGENTA}Ruka: Sampai jumpa, Young Lord. Hamba senantiasa siap sedia mendampingi Anda.{RESET}\n")
                break
            if prompt.lower() in ("/clear", "clear", "cls"):
                os.system("cls" if os.name == "nt" else "clear")
                print_banner()
                continue
            if prompt.lower() in ("/help", "help"):
                print_help()
                continue
            if prompt.lower() in ("/status", "status"):
                handle_status(sock)
            elif prompt.lower() in ("/diff", "diff"):
                handle_diff()
            elif prompt.lower() in ("/git-status", "/gs", "git-status", "gs"):
                handle_git_status()
            elif prompt.lower().startswith("/review ") or prompt.lower().startswith("review "):
                path = prompt.split(None, 1)[1].strip()
                handle_review(sock, path)
            elif prompt.lower().startswith("/search ") or prompt.lower().startswith("search "):
                q = prompt.split(None, 1)[1].strip()
                handle_search(sock, q)
            elif prompt.lower().startswith("/image ") or prompt.lower().startswith("/img "):
                parts = prompt.split(None, 2)
                if len(parts) >= 2:
                    img_p = parts[1].strip()
                    user_q = parts[2].strip() if len(parts) > 2 else "Ruka, periksa dan analisis citra visual ini secara saksama."
                    att = build_image_attachment(img_p)
                    if att:
                        handle_chat(sock, user_q, attachment=att)
                else:
                    print(f"{YELLOW}Gunakan: /image <path-ke-gambar> [instruksi]{RESET}")
            else:
                ok = handle_chat(sock, prompt)
                if not ok:
                    reconnected = get_ipc_connection(timeout=3.0)
                    if reconnected:
                        try:
                            sock.close()
                        except Exception:
                            pass
                        sock, _ = reconnected
                        print(f"{DIM}[✓] Saluran komunikasi dengan Otak Ruka disegarkan kembali.{RESET}\n")
        except (KeyboardInterrupt, EOFError):
            print(f"\n{MAGENTA}Ruka: Pamit mengundurkan diri, Young Lord.{RESET}\n")
            break
        except Exception as repl_err:
            print(f"\n{RED}Terjadi kendala pada terminal: {repl_err}{RESET}")
            reconnected = get_ipc_connection(timeout=3.0)
            if reconnected:
                try:
                    sock.close()
                except Exception:
                    pass
                sock, _ = reconnected


def print_help():
    print_banner()
    print(f"""{BOLD}PENGGUNAAN CLI RUKA CODING AGENT:{RESET}
  {CYAN}ruka{RESET}                        Buka sesi REPL interaktif terminal
  {CYAN}ruka "pesan / perintah"{RESET}    Kirim instruksi coding/tugas ke Ruka
  {CYAN}ruka review <path>{RESET}          Review berkas/kode dengan analisis mendalam
  {CYAN}ruka diff [path]{RESET}            Tampilkan perbedaan kode git diff berwarna
  {CYAN}ruka git-status{RESET}             Periksa ringkasan status git repositori
  {CYAN}ruka status{RESET}                 Cek kesehatan runtime Otak Ruka & PID
  {CYAN}ruka search "query"{RESET}         Cari berita/informasi terkini di Google & Web
  {CYAN}ruka --image <file> "tanya"{RESET} Analisis citra visual/mockup arsitektur (Vision)
  {CYAN}ruka help{RESET}                   Tampilkan bantuan ini

{BOLD}PERINTAH SLASH DI DALAM REPL:{RESET}
  {CYAN}/search <query>{RESET}             Telusuri web/berita real-time
  {CYAN}/image <path> [instruksi]{RESET}  Analisis gambar/desain mockup langsung
  {CYAN}/diff [file]{RESET}                Tampilkan git diff
  {CYAN}/status{RESET}                     Status runtime & sandbox
  {CYAN}/clear{RESET}                      Bersihkan layar terminal
  {CYAN}/exit{RESET}                       Keluar dari sesi terminal

{BOLD}CONTOH CODING:{RESET}
  ruka "Perbaiki race condition di modul auth.py"
  ruka --image screenshot.png "Implementasikan tampilan ini dengan Bootstrap 5"
  ruka search "Dokumentasi Go Fiber terbaru"
  ruka review src/agent/orchestrator.py
  ruka diff
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

    # Ekstraksi opsi gambar multimodal jika ada
    img_attachment = None
    if "--image" in args or "-i" in args:
        flag = "--image" if "--image" in args else "-i"
        idx = args.index(flag)
        if idx + 1 < len(args):
            img_path = args[idx + 1]
            img_attachment = build_image_attachment(img_path)
            args = args[:idx] + args[idx + 2:]

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
            if not prompt and img_attachment:
                prompt = "Ruka, periksa dan analisis citra visual ini secara saksama."
            handle_chat(sock, prompt, attachment=img_attachment)
    finally:
        try:
            sock.close()
        except Exception:
            pass


if __name__ == "__main__":
    main()
