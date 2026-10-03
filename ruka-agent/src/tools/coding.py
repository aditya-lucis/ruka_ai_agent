# -*- coding: utf-8 -*-
"""RUKA Coding Tools — Phase 1 Foundation
Implementasi tool coding berstandar tinggi untuk Ruka (Marquis of Trendamis).
Semua tool mematuhi Path Jail, keamanan sandbox, dan kontrak BaseTool.
"""
from __future__ import annotations

import logging
import os
import re
import subprocess
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, Field
from src.tools.base import BaseTool, ToolError
from src.tools.registry import ToolRegistry

log = logging.getLogger("ruka.tools.coding")


# ============================================================
# Path Jail & Security Sandbox Helpers
# ============================================================
class PathJail:
    """Kurung kerja jalur: memastikan semua manipulasi file dan direktori
    tetap berada di dalam workspace yang diizinkan (mencegah traversal).
    """

    def __init__(self, base: str | Path | None = None) -> None:
        if base is None:
            env_base = os.environ.get("RUKA_WORKSPACE") or os.environ.get("RUKA_PROJECT_ROOT")
            base = env_base if env_base else Path.cwd()
        base_str = str(base).strip().replace("\\", "/")
        if os.name == "nt" and re.match(r"^/[a-zA-Z]/", base_str):
            base_str = re.sub(r"^/([a-zA-Z])/", r"\1:/", base_str)
        self.base = Path(base_str).resolve()
        if not self.base.exists():
            raise ToolError(f"Base path jail tidak ditemukan: {self.base}")

    def confine(self, rel_or_abs: str | Path) -> Path:
        """Mengurung jalur input agar tidak dapat keluar dari self.base."""
        if not rel_or_abs:
            raise ToolError("Jalur path tidak boleh kosong")

        raw_str = str(rel_or_abs).strip().replace("\\", "/")
        if os.name == "nt" and re.match(r"^/[a-zA-Z]/", raw_str):
            raw_str = re.sub(r"^/([a-zA-Z])/", r"\1:/", raw_str)
        p = Path(raw_str)

        if p.is_absolute():
            candidate = p.resolve()
        else:
            candidate = (self.base / raw_str).resolve()

        try:
            candidate.relative_to(self.base)
        except ValueError:
            raise ToolError(
                f"Akses ditolak: Jalur berada di luar kurung kerja (Path Jail): "
                f"{raw_str!r} -> {candidate} (base: {self.base})"
            ) from None

        return candidate


_default_jail: PathJail | None = None


def get_default_jail() -> PathJail:
    """Mendapatkan atau menginisialisasi singleton PathJail bawaan."""
    global _default_jail
    if _default_jail is None:
        _default_jail = PathJail()
    return _default_jail


def set_default_jail(jail: PathJail | None) -> None:
    """Mengubah instance PathJail default (berguna untuk testing/sandbox khusus)."""
    global _default_jail
    _default_jail = jail


def detect_binary(path: Path, peek: int = 512) -> bool:
    """Mendeteksi apakah sebuah file berupa biner atau teks biasa."""
    try:
        if not path.is_file():
            return False
        with path.open("rb") as f:
            chunk = f.read(peek)
        if not chunk:
            return False
        if b"\x00" in chunk:
            return True

        magic_signatures = [
            b"\x89PNG\r\n\x1a\n",
            b"MZ",
            b"\x7fELF",
            b"%PDF",
            b"PK\x03\x04",
            b"GIF8",
            b"\x1f\x8b",
        ]
        return any(chunk.startswith(sig) for sig in magic_signatures)
    except Exception:
        return False


# ============================================================
# 1. read_file
# ============================================================
class ReadFileArgs(BaseModel):
    path: str = Field(description="Path file yang ingin dibaca (relatif atau absolut di dalam workspace)")
    start_line: int | None = Field(default=None, description="Baris awal (1-indexed, inklusif)")
    end_line: int | None = Field(default=None, description="Baris akhir (1-indexed, inklusif)")


class ReadFileTool(BaseTool):
    model_config = ConfigDict(arbitrary_types_allowed=True)
    name: str = "read_file"
    description: str = (
        "Membaca isi file teks. Bisa membaca seluruh file atau hanya rentang baris tertentu. "
        "Gunakan sebelum melakukan edit agar konteks akurat."
    )
    args_model: type[BaseModel] = ReadFileArgs
    timeout_s: float = 10.0
    jail: PathJail | None = None

    def _get_jail(self) -> PathJail:
        return self.jail or get_default_jail()

    def run(self, args: ReadFileArgs) -> dict[str, Any]:
        jail = self._get_jail()
        path = jail.confine(args.path)

        if not path.exists():
            raise ToolError(f"File tidak ditemukan: {args.path}")
        if not path.is_file():
            raise ToolError(f"Bukan file (mungkin direktori): {args.path}")

        if detect_binary(path):
            raise ToolError(f"File biner terdeteksi, tidak dapat dibaca sebagai teks: {args.path}")

        try:
            content = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            content = path.read_text(encoding="latin-1", errors="replace")

        lines = content.splitlines(keepends=True)
        total_lines = len(lines)

        if args.start_line is not None or args.end_line is not None:
            start = max((args.start_line or 1) - 1, 0)
            end = min(args.end_line or total_lines, total_lines)
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
    paths: list[str] = Field(description="Daftar path file yang ingin dibaca sekaligus")
    max_total_chars: int = Field(default=120_000, description="Batas total karakter dari semua file")


class ReadFilesTool(BaseTool):
    model_config = ConfigDict(arbitrary_types_allowed=True)
    name: str = "read_files"
    description: str = "Membaca beberapa file sekaligus dengan batasan total karakter guna efisiensi konteks."
    args_model: type[BaseModel] = ReadFilesArgs
    timeout_s: float = 15.0
    jail: PathJail | None = None

    def _get_jail(self) -> PathJail:
        return self.jail or get_default_jail()

    def run(self, args: ReadFilesArgs) -> dict[str, Any]:
        jail = self._get_jail()
        results: list[dict[str, Any]] = []
        total_chars = 0

        for p in args.paths:
            try:
                path = jail.confine(p)
            except ToolError as e:
                results.append({"path": p, "error": str(e), "truncated": False})
                continue

            if not path.exists() or not path.is_file():
                results.append({"path": str(path), "error": "file tidak ditemukan", "truncated": False})
                continue

            if detect_binary(path):
                results.append({"path": str(path), "error": "file biner diabaikan", "truncated": False})
                continue

            try:
                content = path.read_text(encoding="utf-8", errors="replace")
            except Exception as e:
                results.append({"path": str(path), "error": str(e), "truncated": False})
                continue

            if total_chars + len(content) > args.max_total_chars:
                remaining = max(0, args.max_total_chars - total_chars)
                truncated_content = content[:remaining]
                results.append({
                    "path": str(path),
                    "content": truncated_content,
                    "truncated": True,
                })
                total_chars += len(truncated_content)
                break

            results.append({"path": str(path), "content": content, "truncated": False})
            total_chars += len(content)

        return {"files": results, "total_chars": total_chars}


# ============================================================
# 3. edit_file (Search & Replace)
# ============================================================
class EditFileArgs(BaseModel):
    path: str = Field(description="Path file yang akan diedit")
    old_string: str = Field(description="Teks yang ingin diganti (harus unik jika replace_all=False)")
    new_string: str = Field(description="Teks pengganti yang baru")
    replace_all: bool = Field(default=False, description="Ganti semua kemunculan jika bernilai True")


class EditFileTool(BaseTool):
    model_config = ConfigDict(arbitrary_types_allowed=True)
    name: str = "edit_file"
    description: str = (
        "Melakukan search-and-replace pada file secara presisi. "
        "Sangat disarankan old_string unik. "
        "Jika ditemukan lebih dari satu kemunculan dan replace_all=False, tool akan gagal (aman)."
    )
    args_model: type[BaseModel] = EditFileArgs
    timeout_s: float = 10.0
    jail: PathJail | None = None

    def _get_jail(self) -> PathJail:
        return self.jail or get_default_jail()

    def run(self, args: EditFileArgs) -> dict[str, Any]:
        jail = self._get_jail()
        path = jail.confine(args.path)

        if not path.exists():
            raise ToolError(f"File tidak ditemukan: {args.path}")
        if not path.is_file():
            raise ToolError(f"Bukan file: {args.path}")

        try:
            original = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            original = path.read_text(encoding="latin-1")

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
    content: str = Field(description="Isi lengkap file yang akan ditulis")
    create_if_not_exists: bool = Field(default=True, description="Buat file baru jika belum ada")


class WriteFileTool(BaseTool):
    model_config = ConfigDict(arbitrary_types_allowed=True)
    name: str = "write_file"
    description: str = "Menulis atau menimpa seluruh isi file teks secara terstruktur."
    args_model: type[BaseModel] = WriteFileArgs
    timeout_s: float = 10.0
    jail: PathJail | None = None

    def _get_jail(self) -> PathJail:
        return self.jail or get_default_jail()

    def run(self, args: WriteFileArgs) -> dict[str, Any]:
        jail = self._get_jail()
        path = jail.confine(args.path)

        if not args.create_if_not_exists and not path.exists():
            raise ToolError(f"File tidak ada dan create_if_not_exists=False: {args.path}")

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
    command: str = Field(description="Perintah shell yang akan dijalankan")
    working_directory: str | None = Field(default=None, description="Direktori kerja (harus di dalam workspace)")
    timeout_seconds: int = Field(default=60, ge=1, le=300, description="Batas waktu eksekusi dalam detik")
    require_confirmation: bool = Field(
        default=False,
        description="Harus diset True untuk menjalankan perintah yang berpotensi destruktif/berbahaya"
    )


class RunTerminalTool(BaseTool):
    model_config = ConfigDict(arbitrary_types_allowed=True)
    name: str = "run_terminal"
    description: str = (
        "Menjalankan perintah terminal/shell. "
        "Gunakan dengan hati-hati. Perintah berbahaya wajib require_confirmation=True."
    )
    args_model: type[BaseModel] = RunTerminalArgs
    timeout_s: float = 305.0
    requires_permission: bool = True
    jail: PathJail | None = None

    DANGEROUS_PATTERNS: list[str] = [
        r"rm\s+-rf",
        r"git\s+push\s+.*--force",
        r"git\s+reset\s+--hard",
        r"mkfs",
        r"dd\s+if=",
        r":\(\)\{\s*:\|:\&\s*\};:",
        r"del\s+/[sfq]",
        r"format\s+[a-z]:",
        r"Remove-Item.*-Recurse.*-Force",
        r"drop\s+database",
    ]

    def _get_jail(self) -> PathJail:
        return self.jail or get_default_jail()

    def run(self, args: RunTerminalArgs) -> dict[str, Any]:
        for pattern in self.DANGEROUS_PATTERNS:
            if re.search(pattern, args.command, re.IGNORECASE):
                if not args.require_confirmation:
                    raise ToolError(
                        "Perintah berbahaya terdeteksi. "
                        "Set require_confirmation=True dan minta izin Young Lord terlebih dahulu."
                    )

        jail = self._get_jail()
        if args.working_directory:
            cwd = jail.confine(args.working_directory)
        else:
            cwd = jail.base

        if not cwd.exists() or not cwd.is_dir():
            raise ToolError(f"Working directory tidak ditemukan atau bukan direktori: {cwd}")

        try:
            result = subprocess.run(
                args.command,
                shell=True,
                cwd=str(cwd),
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
                "cwd": str(cwd),
            }
        except subprocess.TimeoutExpired:
            raise ToolError(f"Perintah timeout setelah {args.timeout_seconds} detik")


# ============================================================
# 6. list_dir
# ============================================================
class ListDirArgs(BaseModel):
    path: str = Field(default=".", description="Direktori yang ingin dilihat isinya (default: root workspace)")


class ListDirTool(BaseTool):
    model_config = ConfigDict(arbitrary_types_allowed=True)
    name: str = "list_dir"
    description: str = "Menampilkan isi direktori (daftar file dan sub-folder)."
    args_model: type[BaseModel] = ListDirArgs
    timeout_s: float = 5.0
    jail: PathJail | None = None

    def _get_jail(self) -> PathJail:
        return self.jail or get_default_jail()

    def run(self, args: ListDirArgs) -> dict[str, Any]:
        jail = self._get_jail()
        path = jail.confine(args.path)

        if not path.exists():
            raise ToolError(f"Path tidak ditemukan: {args.path}")
        if not path.is_dir():
            raise ToolError(f"Bukan direktori: {args.path}")

        entries: list[dict[str, Any]] = []
        try:
            for item in sorted(path.iterdir(), key=lambda p: (not p.is_dir(), p.name.lower())):
                entries.append({
                    "name": item.name,
                    "type": "dir" if item.is_dir() else "file",
                    "size": item.stat().st_size if item.is_file() else None,
                })
        except Exception as e:
            raise ToolError(f"Gagal membaca isi direktori {args.path}: {e}")

        return {"path": str(path), "entries": entries}


# ============================================================
# 7. grep
# ============================================================
class GrepArgs(BaseModel):
    pattern: str = Field(description="Pola teks atau regex yang dicari")
    path: str = Field(default=".", description="Direktori atau file target pencarian")
    glob: str | None = Field(default=None, description="Filter nama file, contoh: '*.py' atau '*.ts'")
    case_insensitive: bool = Field(default=False, description="Abaikan perbedaan huruf besar dan kecil")
    max_results: int = Field(default=50, ge=1, le=200, description="Batas maksimum hasil temuan")


class GrepTool(BaseTool):
    model_config = ConfigDict(arbitrary_types_allowed=True)
    name: str = "grep"
    description: str = "Mencari teks atau pola regex di dalam file secara cepat dan mendalam."
    args_model: type[BaseModel] = GrepArgs
    timeout_s: float = 15.0
    jail: PathJail | None = None

    IGNORE_DIRS: set[str] = {".git", ".venv", "venv", "__pycache__", "node_modules", "dist", "build"}

    def _get_jail(self) -> PathJail:
        return self.jail or get_default_jail()

    def run(self, args: GrepArgs) -> dict[str, Any]:
        jail = self._get_jail()
        root = jail.confine(args.path)

        if not root.exists():
            raise ToolError(f"Path target grep tidak ditemukan: {args.path}")

        flags = re.IGNORECASE if args.case_insensitive else 0
        try:
            regex = re.compile(args.pattern, flags)
        except re.error as e:
            raise ToolError(f"Pola regex tidak valid: {e}")

        matches: list[dict[str, Any]] = []

        def should_search(p: Path) -> bool:
            if args.glob and not p.match(args.glob):
                return False
            return True

        if root.is_file():
            files_to_check = [root]
        else:
            files_to_check = []
            for current_root, dirs, files in os.walk(root):
                dirs[:] = [d for d in dirs if d not in self.IGNORE_DIRS]
                for file_name in files:
                    file_path = Path(current_root) / file_name
                    if should_search(file_path):
                        files_to_check.append(file_path)

        for file_path in files_to_check:
            if detect_binary(file_path):
                continue
            try:
                text = file_path.read_text(encoding="utf-8", errors="ignore")
                for i, line in enumerate(text.splitlines(), 1):
                    if regex.search(line):
                        matches.append({
                            "file": str(file_path.relative_to(jail.base)).replace("\\", "/"),
                            "line": i,
                            "content": line.strip()[:200],
                        })
                        if len(matches) >= args.max_results:
                            return {"matches": matches, "truncated": True}
            except Exception:
                continue

        return {"matches": matches, "truncated": False}


# ============================================================
# 8. glob
# ============================================================
class GlobArgs(BaseModel):
    pattern: str = Field(description="Pola glob untuk mencari file/folder, contoh: '**/*.py', 'src/*.ts'")
    path: str = Field(default=".", description="Direktori awal pencarian")
    max_results: int = Field(default=100, ge=1, le=500, description="Batas maksimum hasil temuan")


class GlobTool(BaseTool):
    model_config = ConfigDict(arbitrary_types_allowed=True)
    name: str = "glob"
    description: str = "Mencari file dan folder berdasarkan pola glob di dalam workspace."
    args_model: type[BaseModel] = GlobArgs
    timeout_s: float = 10.0
    jail: PathJail | None = None

    IGNORE_DIRS: set[str] = {".git", ".venv", "venv", "__pycache__", "node_modules", "dist", "build"}

    def _get_jail(self) -> PathJail:
        return self.jail or get_default_jail()

    def run(self, args: GlobArgs) -> dict[str, Any]:
        jail = self._get_jail()
        root = jail.confine(args.path)

        if not root.exists():
            raise ToolError(f"Path tidak ditemukan: {args.path}")
        if not root.is_dir():
            raise ToolError(f"Bukan direktori: {args.path}")

        matches: list[str] = []
        truncated = False

        matched_items = root.glob(args.pattern)
        for item in matched_items:
            try:
                rel_parts = item.relative_to(root).parts
                if any(part in self.IGNORE_DIRS for part in rel_parts):
                    continue
                matches.append(str(item.relative_to(jail.base)).replace("\\", "/"))
                if len(matches) >= args.max_results:
                    truncated = True
                    break
            except Exception:
                continue

        return {
            "path": str(root),
            "pattern": args.pattern,
            "matches": matches,
            "total_matches": len(matches),
            "truncated": truncated,
        }


# ============================================================
# Tool Registration Helper
# ============================================================
def register_coding_tools(
    registry: ToolRegistry,
    jail: PathJail | None = None
) -> list[BaseTool]:
    """Mendaftarkan seluruh fondasi tool coding Phase 1 ke dalam ToolRegistry."""
    tools: list[BaseTool] = [
        ReadFileTool(jail=jail),
        ReadFilesTool(jail=jail),
        EditFileTool(jail=jail),
        WriteFileTool(jail=jail),
        RunTerminalTool(jail=jail),
        ListDirTool(jail=jail),
        GrepTool(jail=jail),
        GlobTool(jail=jail),
    ]
    for tool in tools:
        registry.register(tool)
    return tools
