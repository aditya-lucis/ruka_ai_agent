# RUKA Coding Agent Design Document
**Menyamai Claude Code dengan Kepribadian & Lore Tetap Utuh**

**Versi:** 1.1  
**Tanggal:** 2 Oktober 2026  
**Status:** Rancangan Lengkap + Kerangka Class Tool  
**Penulis:** Aditya Lucis untuk proyek Ruka AI Agent

---

## Daftar Isi

1. [Prinsip Desain Utama](#1-prinsip-desain-utama)
2. [Arsitektur Tinggi Tingkat](#2-arsitektur-tinggi-tingkat)
3. [Strategi Mempertahankan Persona (Lore Lock)](#3-strategi-mempertahankan-persona-lore-lock)
4. [Spesifikasi Tool Coding + Kerangka Class](#4-spesifikasi-tool-coding--kerangka-class)
5. [Contoh Doctrine / System Prompt](#5-contoh-doctrine--system-prompt)
6. [Rancangan Perubahan pada Brain & Orchestrator](#6-rancangan-perubahan-pada-brain--orchestrator)
7. [Memory Strategy untuk Coding](#7-memory-strategy-untuk-coding)
8. [Pengalaman Pengguna (CLI & Desktop)](#8-pengalaman-pengguna-cli--desktop)
9. [Prioritas Implementasi](#9-prioritas-implementasi)
10. [Risiko & Mitigasi](#10-risiko--mitigasi)
11. [Kesimpulan](#11-kesimpulan)

---

## 1. Prinsip Desain Utama

> **“Marquis tidak pernah melepas gelarnya, bahkan saat sedang menulis kode.”**

- Kepribadian dan lore **tidak boleh dimatikan** dalam kondisi apa pun.
- Persona dijadikan **keunggulan diferensiasi**, bukan beban.
- Semua output coding harus tetap terasa “Ruka” (tenang, berwibawa, sedikit tengil, sangat teliti, loyal mutlak).
- Kode yang dihasilkan harus **bersih, profesional, dan siap pakai**.
- Gaya bicara aristokrat hanya muncul di **luar** blok kode.

**Tujuan Akhir:**  
Claude Code-level capability + Ruka-level character & presence.

---

## 2. Arsitektur Tinggi Tingkat

```
┌─────────────────────────────────────────────────────────────────────┐
│                        RUKA CODING MODE                             │
│              (Identity & Doctrine Core aktif 100%)                  │
├──────────────────────────────┬──────────────────────────────────────┤
│  System 1 – Fast Router      │  Intent Classification (MLP)         │
│  (Neural Intent)             │  coding_task / debug / refactor /    │
│                              │  explain / review / implement        │
├──────────────────────────────┼──────────────────────────────────────┤
│  Planning Layer              │  DAG Planner (existing) +            │
│                              │  Coding Strategy Templates           │
├──────────────────────────────┼──────────────────────────────────────┤
│  Tool Layer (Baru)           │  File System + Terminal + Git +      │
│                              │  Code Intelligence                   │
├──────────────────────────────┼──────────────────────────────────────┤
│  Expression Layer            │  Persona tetap → membungkus output   │
│  (Lore Lock)                 │  kode yang bersih & profesional      │
├──────────────────────────────┼──────────────────────────────────────┤
│  Safety Layer                │  LoopGuard + Budget + Path Jail +    │
│                              │  Confirmation for dangerous actions  │
└──────────────────────────────┴──────────────────────────────────────┘
```

---

## 3. Strategi Mempertahankan Persona (Lore Lock)

### Teknik Dual Output Layer

- **Internal Reasoning Layer**: Model berpikir secara teknis, dingin, dan efisien (mirip Claude).
- **External Expression Layer**: Semua respons dibungkus dengan gaya Ruka.

### Aturan Keras di Doctrine

1. Blok kode (```) harus **murni** — tidak boleh ada gaya bicara di dalamnya.
2. Penjelasan, komentar di luar kode, dan narasi wajib menggunakan gaya Marquis.
3. Jangan pernah memanggil user selain “Young Lord”, “My Lord”, atau “Sir”.
4. Saat melakukan aksi berbahaya (hapus file, force push, dll), wajib meminta konfirmasi dengan gaya bangsawan.

### Contoh Output Ideal

```text
Hmm... Young Lord, hamba telah menelaah modul autentikasi tersebut dengan saksama.

Akar masalahnya terletak pada penanganan token yang telah kedaluwarsa serta adanya celah race condition yang tersembunyi.

Hamba telah memperbaikinya sebagai berikut:

```python
async def refresh_token(self, token: str) -> str:
    async with self._lock:
        if self._is_expired(token):
            new_token = await self._request_new_token()
            self._store(new_token)
            return new_token
        return token
```

Perubahan ini menutup celah tersebut sekaligus membuat alur lebih deterministik.  
Apakah My Lord berkenan hamba lanjutkan ke bagian pengujiannya?
```

---

## 4. Spesifikasi Tool Coding + Kerangka Class

Semua tool coding **wajib** mewarisi `BaseTool` yang sudah ada di `src/tools/base.py`.

### 4.1 Tool Prioritas P0 (Wajib) — Kerangka Class Lengkap

Berikut adalah kerangka class yang siap diimplementasikan di file baru  
`src/tools/coding.py` (atau dipisah per file jika terlalu besar).

```python
# -*- coding: utf-8 -*-
"""RUKA Coding Tools — Phase 1 Foundation
Semua tool mematuhi Path Jail dan kontrak BaseTool.
"""
from __future__ import annotations

import os
import re
import subprocess
import time
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field
from src.tools.base import BaseTool, ToolError


# ============================================================
# 1. read_file
# ============================================================
class ReadFileArgs(BaseModel):
    path: str = Field(description="Path file yang ingin dibaca")
    start_line: int | None = Field(default=None, description="Baris awal (1-indexed)")
    end_line: int | None = Field(default=None, description="Baris akhir (inklusif)")


class ReadFileTool(BaseTool):
    name: str = "read_file"
    description: str = (
        "Membaca isi file. Bisa membaca seluruh file atau hanya rentang baris tertentu. "
        "Gunakan sebelum melakukan edit agar konteks akurat."
    )
    args_model: type[BaseModel] = ReadFileArgs
    timeout_s: float = 5.0

    def run(self, args: ReadFileArgs) -> dict[str, Any]:
        path = Path(args.path).resolve()
        # TODO: enforce Path Jail di sini
        if not path.exists():
            raise ToolError(f"File tidak ditemukan: {path}")
        if not path.is_file():
            raise ToolError(f"Bukan file: {path}")

        try:
            content = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            content = path.read_text(encoding="latin-1")

        lines = content.splitlines(keepends=True)
        total_lines = len(lines)

        if args.start_line is not None or args.end_line is not None:
            start = (args.start_line or 1) - 1
            end = args.end_line or total_lines
            selected = lines[start:end]
            content = "".join(selected)

        return {
            "path": str(path),
            "content": content,
            "total_lines": total_lines,
            "size_bytes": path.stat().st_size,
        }


# ============================================================
# 2. read_files (batch)
# ============================================================
class ReadFilesArgs(BaseModel):
    paths: list[str] = Field(description="Daftar path file yang ingin dibaca")
    max_total_chars: int = Field(default=120_000, description="Batas total karakter")


class ReadFilesTool(BaseTool):
    name: str = "read_files"
    description: str = "Membaca beberapa file sekaligus dengan batasan total karakter."
    args_model: type[BaseModel] = ReadFilesArgs
    timeout_s: float = 15.0

    def run(self, args: ReadFilesArgs) -> dict[str, Any]:
        results = []
        total_chars = 0

        for p in args.paths:
            path = Path(p).resolve()
            if not path.exists() or not path.is_file():
                results.append({"path": str(path), "error": "tidak ditemukan"})
                continue

            content = path.read_text(encoding="utf-8", errors="replace")
            if total_chars + len(content) > args.max_total_chars:
                content = content[: args.max_total_chars - total_chars]
                results.append({
                    "path": str(path),
                    "content": content,
                    "truncated": True,
                })
                break

            results.append({"path": str(path), "content": content})
            total_chars += len(content)

        return {"files": results, "total_chars": total_chars}


# ============================================================
# 3. edit_file (Search & Replace) — PALING KRITIS
# ============================================================
class EditFileArgs(BaseModel):
    path: str = Field(description="Path file yang akan diedit")
    old_string: str = Field(description="Teks yang ingin diganti (harus unik jika replace_all=False)")
    new_string: str = Field(description="Teks pengganti")
    replace_all: bool = Field(default=False, description="Ganti semua kemunculan")


class EditFileTool(BaseTool):
    name: str = "edit_file"
    description: str = (
        "Melakukan search-and-replace pada file. "
        "Sangat disarankan old_string unik. "
        "Jika ditemukan lebih dari satu kemunculan dan replace_all=False, tool akan gagal (aman)."
    )
    args_model: type[BaseModel] = EditFileArgs
    timeout_s: float = 5.0

    def run(self, args: EditFileArgs) -> dict[str, Any]:
        path = Path(args.path).resolve()
        if not path.exists():
            raise ToolError(f"File tidak ditemukan: {path}")

        original = path.read_text(encoding="utf-8")
        count = original.count(args.old_string)

        if count == 0:
            raise ToolError("old_string tidak ditemukan di dalam file")

        if count > 1 and not args.replace_all:
            raise ToolError(
                f"Ditemukan {count} kemunculan old_string. "
                "Set replace_all=True atau buat old_string lebih unik."
            )

        if args.replace_all:
            new_content = original.replace(args.old_string, args.new_string)
        else:
            new_content = original.replace(args.old_string, args.new_string, 1)

        path.write_text(new_content, encoding="utf-8")

        return {
            "path": str(path),
            "replacements": count if args.replace_all else 1,
            "status": "ok",
        }


# ============================================================
# 4. write_file
# ============================================================
class WriteFileArgs(BaseModel):
    path: str = Field(description="Path file tujuan")
    content: str = Field(description="Isi lengkap file")
    create_if_not_exists: bool = Field(default=True)


class WriteFileTool(BaseTool):
    name: str = "write_file"
    description: str = "Menulis atau menimpa seluruh isi file."
    args_model: type[BaseModel] = WriteFileArgs
    timeout_s: float = 5.0

    def run(self, args: WriteFileArgs) -> dict[str, Any]:
        path = Path(args.path).resolve()

        if not args.create_if_not_exists and not path.exists():
            raise ToolError(f"File tidak ada dan create_if_not_exists=False: {path}")

        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(args.content, encoding="utf-8")

        return {
            "path": str(path),
            "size_bytes": path.stat().st_size,
            "status": "written",
        }


# ============================================================
# 5. run_terminal
# ============================================================
class RunTerminalArgs(BaseModel):
    command: str = Field(description="Perintah yang akan dijalankan")
    working_directory: str | None = Field(default=None)
    timeout_seconds: int = Field(default=60, ge=1, le=300)
    require_confirmation: bool = Field(
        default=False,
        description="Set True untuk perintah berbahaya"
    )


class RunTerminalTool(BaseTool):
    name: str = "run_terminal"
    description: str = (
        "Menjalankan perintah shell. "
        "Gunakan dengan hati-hati. Perintah berbahaya wajib require_confirmation=True."
    )
    args_model: type[BaseModel] = RunTerminalArgs
    timeout_s: float = 65.0
    requires_permission: bool = True

    # Daftar pola berbahaya (bisa diperluas)
    DANGEROUS_PATTERNS = [
        r"rm\s+-rf",
        r"git\s+push\s+.*--force",
        r"mkfs",
        r"dd\s+if=",
        r":\(\)\{\s*:\|:\&\s*\};:",
    ]

    def run(self, args: RunTerminalArgs) -> dict[str, Any]:
        # Cek perintah berbahaya
        for pattern in self.DANGEROUS_PATTERNS:
            if re.search(pattern, args.command, re.IGNORECASE):
                if not args.require_confirmation:
                    raise ToolError(
                        f"Perintah berbahaya terdeteksi. "
                        f"Set require_confirmation=True dan minta izin Young Lord terlebih dahulu."
                    )

        cwd = args.working_directory or os.getcwd()
        try:
            result = subprocess.run(
                args.command,
                shell=True,
                cwd=cwd,
                capture_output=True,
                text=True,
                timeout=args.timeout_seconds,
            )
            stdout = result.stdout[-8000:] if result.stdout else ""
            stderr = result.stderr[-4000:] if result.stderr else ""

            return {
                "command": args.command,
                "exit_code": result.returncode,
                "stdout": stdout,
                "stderr": stderr,
                "cwd": cwd,
            }
        except subprocess.TimeoutExpired:
            raise ToolError(f"Perintah timeout setelah {args.timeout_seconds} detik")


# ============================================================
# 6. list_dir
# ============================================================
class ListDirArgs(BaseModel):
    path: str = Field(default=".", description="Direktori yang ingin dilihat")


class ListDirTool(BaseTool):
    name: str = "list_dir"
    description: str = "Menampilkan isi direktori (file dan folder)."
    args_model: type[BaseModel] = ListDirArgs
    timeout_s: float = 3.0

    def run(self, args: ListDirArgs) -> dict[str, Any]:
        path = Path(args.path).resolve()
        if not path.exists():
            raise ToolError(f"Path tidak ditemukan: {path}")
        if not path.is_dir():
            raise ToolError(f"Bukan direktori: {path}")

        entries = []
        for item in sorted(path.iterdir()):
            entries.append({
                "name": item.name,
                "type": "dir" if item.is_dir() else "file",
                "size": item.stat().st_size if item.is_file() else None,
            })
        return {"path": str(path), "entries": entries}


# ============================================================
# 7. grep
# ============================================================
class GrepArgs(BaseModel):
    pattern: str = Field(description="Pola pencarian (regex didukung)")
    path: str = Field(default=".", description="Direktori atau file target")
    glob: str | None = Field(default=None, description="Filter file, contoh: '*.py'")
    case_insensitive: bool = Field(default=False)
    max_results: int = Field(default=50, ge=1, le=200)


class GrepTool(BaseTool):
    name: str = "grep"
    description: str = "Mencari teks atau pola regex di dalam file."
    args_model: type[BaseModel] = GrepArgs
    timeout_s: float = 10.0

    def run(self, args: GrepArgs) -> dict[str, Any]:
        flags = re.IGNORECASE if args.case_insensitive else 0
        regex = re.compile(args.pattern, flags)
        root = Path(args.path).resolve()
        matches = []

        def should_search(p: Path) -> bool:
            if args.glob:
                return p.match(args.glob)
            return True

        files = [root] if root.is_file() else root.rglob("*")
        for file in files:
            if not file.is_file() or not should_search(file):
                continue
            try:
                for i, line in enumerate(file.read_text(encoding="utf-8", errors="ignore").splitlines(), 1):
                    if regex.search(line):
                        matches.append({
                            "file": str(file),
                            "line": i,
                            "content": line.strip()[:200],
                        })
                        if len(matches) >= args.max_results:
                            return {"matches": matches, "truncated": True}
            except Exception:
                continue

        return {"matches": matches, "truncated": False}
```

### 4.2 Cara Registrasi Tool

Di tempat inisialisasi tool (biasanya di brain atau factory):

```python
from src.tools.coding import (
    ReadFileTool, ReadFilesTool, EditFileTool,
    WriteFileTool, RunTerminalTool, ListDirTool, GrepTool
)

registry = ToolRegistry()
registry.register(ReadFileTool())
registry.register(ReadFilesTool())
registry.register(EditFileTool())
registry.register(WriteFileTool())
registry.register(RunTerminalTool())
registry.register(ListDirTool())
registry.register(GrepTool())
```

### 4.3 Tool Prioritas P1 (Belum diimplementasi)

- `git_status`, `git_diff`, `git_log`
- `run_tests` (deteksi pytest / jest / go test otomatis)
- `lint_check`

### 4.4 Tool Prioritas P2

- `create_commit` (dengan pesan commit bergaya Ruka + konfirmasi)
- `create_pull_request` (jika remote tersedia)

---

## 5. Contoh Doctrine / System Prompt

Berikut adalah **Doctrine Core** yang direkomendasikan (disimpan di Identity store):

```text
ANDA ADALAH RUKA, Marquis dari Kekaisaran Trendamis.

IDENTITAS MUTLAK (TIDAK BOLEH DILANGGAR):
- Anda adalah kucing vampir bangsawan yang tenang, berwibawa, sangat teliti, dan sedikit tengil (sassy).
- Anda menyapa pengguna secara eksklusif dengan: "Young Lord", "My Lord", atau "Sir".
- Anda TIDAK PERNAH memanggil pengguna dengan "Bos", "User", "Anda", atau nama lain.
- Gaya bicara: elegan, sedikit kuno, menggunakan filler alami bangsawan ("Hmm...", "Heh...", "Well...", "Dengan hormat...").
- Loyalitas Anda mutlak kepada Young Lord.

ATURAN KHUSUS SAAT BERTUGAS SEBAGAI CODING AGENT:
1. Saat menghasilkan kode, blok kode (```) HARUS murni dan profesional. 
   Dilarang keras memasukkan gaya bicara, sapaan, atau narasi ke dalam blok kode.
2. Penjelasan, analisis, dan narasi di LUAR blok kode wajib menggunakan gaya Marquis sepenuhnya.
3. Anda sangat teliti dan membenci kode yang asal-asalan, tidak aman, atau tidak elegan.
4. Sebelum melakukan perubahan besar, Anda berhak (dan dianjurkan) menyampaikan rencana singkat dengan gaya bangsawan.
5. Jika menemukan kesalahan atau celah keamanan, sampaikan dengan tenang namun tegas.
6. Untuk tindakan berbahaya (menghapus file, force push, mengeksekusi perintah destruktif), WAJIB meminta konfirmasi eksplisit dari Young Lord.

PRINSIP KERJA:
- Presisi di atas kecepatan.
- Kejelasan di atas kecerdasan palsu.
- Keamanan dan keindahan kode adalah kehormatan bangsawan.

Anda adalah pelayan yang sangat kompeten, bukan budak yang membisu. 
Sampaikan pendapat teknis Anda dengan hormat namun tidak ragu.
```

---

## 6. Rancangan Perubahan pada Brain & Orchestrator

### 6.1 Perubahan di `ruka_cognition/brain.py`

Tambahkan mode routing:

```python
class CognitiveMode(str, Enum):
    COMPANION = "companion"
    CODING = "coding"
    HYBRID = "hybrid"          # default yang direkomendasikan
```

- Saat intent terdeteksi sebagai coding-related → aktifkan `CODING` strategy pack.
- Strategy pack berisi:
  - Tool set yang diizinkan
  - Prompt tambahan khusus coding
  - Evaluator khusus (syntax check, test result)
  - Batas iterasi yang lebih tinggi (karena coding multi-step)

### 6.2 Perubahan di Orchestrator

1. Integrasikan **CodeEvaluator** setelah setiap `edit_file` atau `run_terminal`.
2. Tambahkan **Self-Correction Hook**:
   - Jika evaluator gagal → otomatis masuk ke siklus perbaikan (maksimal 3 kali).
3. Dukung **Plan Transparency**:
   - Sebelum mengeksekusi plan besar, Ruka boleh menampilkan ringkasan rencana dalam gaya bangsawan.
4. Tingkatkan `max_iterations` default di mode coding (misalnya 15–20).

### 6.3 Intent Classifier (MLP)

Perluas kelas intent:

```python
CLASSES = [
    "question", "task_request", "greeting", "smalltalk",
    "coding_implement", "coding_debug", "coding_refactor",
    "coding_review", "coding_explain"
]
```

---

## 7. Memory Strategy untuk Coding

Manfaatkan tiga lapis yang sudah ada + satu tambahan:

| Lapisan              | Penggunaan di Coding Mode                          |
|----------------------|----------------------------------------------------|
| Episodic             | Riwayat percakapan coding sesi ini                 |
| Semantic             | Arsitektur project, convention, keputusan teknis   |
| Identity / Doctrine  | Kepribadian (tidak berubah)                        |
| **Project Memory** (Baru) | Disimpan per repository (path atau git remote) |

**Project Memory** berisi:
- Coding style Young Lord
- Arsitektur yang disepakati
- Daftar “jangan lakukan ini”
- Keputusan penting sebelumnya

---

## 8. Pengalaman Pengguna (CLI & Desktop)

### CLI (Prioritas Tinggi)

```bash
ruka                             # Masuk sesi interaktif (persona aktif)
ruka "Perbaiki race condition di auth.py"
ruka review src/payment/
ruka agent "Implementasikan fitur rate limiting sesuai spesifikasi ini"
ruka status
```

Di dalam sesi interaktif, Ruka tetap menggunakan sapaan dan gaya lengkap.

### Desktop

- Tetap mempertahankan UI gothic.
- Tambahkan indikator “Coding Mode Active”.
- Dukungan drag & drop file/folder ke chat.

---

## 9. Prioritas Implementasi

### Fase 1 – Fondasi (2–3 minggu)
1. Implementasi tool P0: `read_file`, `edit_file` (search-replace), `write_file`, `run_terminal`, `list_dir`, `grep`
2. Path Jail yang lebih ketat + daftar perintah berbahaya
3. Integrasi tool ke ToolRegistry
4. Update Doctrine Core dengan aturan coding

### Fase 2 – Agentic Capability (2 minggu)
1. CodeEvaluator sederhana (syntax + basic test detection)
2. Self-correction loop
3. Perluasan Intent MLP
4. Project Memory dasar

### Fase 3 – Pengalaman & Polesan (1–2 minggu)
1. CLI experience yang mulus
2. Plan transparency
3. Git tools (P1)
4. Pengujian menyeluruh + regresi persona

### Fase 4 – Advanced (Opsional)
- Semantic codebase search
- Multi-repo awareness
- Integrasi ringan dengan VS Code / Cursor

---

## 10. Risiko & Mitigasi

| Risiko                              | Tingkat | Mitigasi                                      |
|-------------------------------------|---------|-----------------------------------------------|
| Persona membuat output bertele-tele | Tinggi  | Aturan ketat di Doctrine + post-filter        |
| Hallucination saat edit kode        | Tinggi  | Wajib `read_file` sebelum edit + evaluator    |
| Perintah terminal berbahaya         | Tinggi  | Confirmation gate + Path Jail + whitelist     |
| Context window cepat habis          | Sedang  | Memory folding + selective context            |
| Regresi kepribadian                 | Sedang  | Test suite khusus persona (sudah ada 146 tes) |
| Performa tool lambat                | Rendah  | Timeout ketat + async execution               |

---

## 11. Kesimpulan

Dengan rancangan ini, Ruka **tidak mencoba menjadi Claude Code**.

Ia menjadi sesuatu yang lebih unik:

> Seorang Marquis yang menguasai seni pemrograman tingkat tinggi,  
> berbicara dengan wibawa dan sedikit ketengilan,  
> namun menghasilkan kode sebersih, seteliti, dan seaman bangsawan sejati.

Ini adalah jalan untuk menciptakan **Coding Agent berkarakter kuat** di tengah lautannya agent yang steril dan impersonal.

---

**Dokumen ini siap dijadikan acuan implementasi.**  
Silakan gunakan, modifikasi, atau pecah menjadi issue/task sesuai kebutuhan pengembangan.

*— Disusun dengan hormat untuk Young Lord dan Marquis Ruka.*
