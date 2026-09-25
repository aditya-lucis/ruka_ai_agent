# -*- coding: utf-8 -*-
"""Configuration v0.3.1 — single source of truth, validated at startup.
v0.3.1 (Patch 1.1): MEMUAT .env sungguhan (bug v0.3: file dibuat tapi
tidak pernah dibaca). Loader stdlib-only — tanpa dependensi baru.
Urutan prioritas: proses env NYATA menang atas .env (12-factor).
"""

from __future__ import annotations
import os
from dataclasses import dataclass
from pathlib import Path

VALID_ENVIRONMENTS = frozenset({"development", "staging", "production"})
DEFAULT_MODEL = "gemini-3.6-flash"
DEFAULT_TTS_MODEL = "gemini-3.1-flash-tts-preview"
DEFAULT_LIVE_MODEL = "gemini-3.1-flash-live-preview"

class ConfigError(RuntimeError):
    """Raised when the environment is unusable — fail fast, fail loud."""

def _load_env_file(path: Path) -> dict[str, str]:
    """Parser .env minimalis, murni stdlib (tanpa python-dotenv).
    Aturan (kompatibel dengan format dotenv umum):
    - `#` di awal baris = komentar; baris kosong diabaikan.
    - `KEY=VALUE`; spasi di sekitar = dan VALUE di-strip.
    - VALUE boleh dibungkus "..." atau '...' — kutip dibuang.
    - Baris tanpa '=' atau KEY kosong -> ValueError (fail loud, bukan senyap).
    - Tidak ada interpolasi/substitusi variabel (kesengajaan: perilaku
      harus deterministik dan mudah diaudit).
    """
    values: dict[str, str] = {}
    if not path.exists():
        return values
    for lineno, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            raise ConfigError(f".env baris {lineno} tanpa '=': {line[:40]!r}")
        key, _, value = line.partition("=")
        key = key.strip()
        if not key or " " in key:
            raise ConfigError(f".env baris {lineno}: kunci tidak sah: {key!r}")
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
            value = value[1:-1]
        values[key] = value
    return values

@dataclass(frozen=True)
class Settings:
    api_key: str
    model: str
    environment: str
    tts_model: str
    voice: str
    live_model: str
    max_iterations: int
    token_budget: int

    def safe_snapshot(self) -> dict:
        """Config without secrets — for traces and logs."""
        return {
            "model": self.model,
            "environment": self.environment,
            "tts_model": self.tts_model,
            "voice": self.voice,
            "live_model": self.live_model,
            "max_iterations": self.max_iterations,
            "token_budget": self.token_budget,
            "api_key_present": bool(self.api_key),
        }

def load_settings(env: dict[str, str] | None = None,
                  dotenv_path: Path | None = None) -> Settings:
    """Load + validate. Call exactly once at process start.
    Urutan pencampuran (prioritas menang):
    1. proses env nyata (os.environ) / argumen `env` (test)
    2. file .env
    Artinya: developer bisa meng-override satu variabel dari shell tanpa
    menyentuh .env, dan CI tetap deterministik.
    """
    if env is not None:
        e = dict(env)
    else:
        if dotenv_path is None:
            dotenv_path = Path(".env")
        file_env = _load_env_file(dotenv_path)
        overrides = {k: v for k, v in os.environ.items() if v != ""}
        e = {**file_env, **overrides}
    api_key = e.get("GEMINI_API_KEY", "").strip()
    if not api_key:
        raise ConfigError(
            "GEMINI_API_KEY kosong atau tidak diset. Pastikan .env ada di "
            "root proyek (salin .env.example) ATAU export variabelnya. "
            "Jangan pernah hardcode kunci di kode."
        )

    environment = e.get("RUKA_ENVIRONMENT", "development").strip().lower()
    if environment not in VALID_ENVIRONMENTS:
        raise ConfigError(
            f"RUKA_ENVIRONMENT='{environment}' tidak sah. "
            f"Pilihan valid: {sorted(VALID_ENVIRONMENTS)}."
        )

    return Settings(
        api_key=api_key,
        model=e.get("RUKA_MODEL", DEFAULT_MODEL).strip() or DEFAULT_MODEL,
        environment=environment,
        tts_model=e.get("RUKA_TTS_MODEL", DEFAULT_TTS_MODEL).strip() or DEFAULT_TTS_MODEL,
        voice=e.get("RUKA_VOICE", "Sulafat").strip() or "Sulafat",
        live_model=e.get("RUKA_LIVE_MODEL", DEFAULT_LIVE_MODEL).strip() or DEFAULT_LIVE_MODEL,
        max_iterations=_positive_int(e.get("RUKA_MAX_ITERATIONS"), 12),
        token_budget=_positive_int(e.get("RUKA_TOKEN_BUDGET"), 60_000),
    )

def _positive_int(raw: str | None, default: int) -> int:
    if raw is None or not raw.strip():
        return default
    try:
        value = int(raw)
    except ValueError as exc:
        raise ConfigError(f"Nilai integer tidak sah: '{raw}'") from exc
    if value <= 0:
        raise ConfigError(f"Nilai harus positif: '{raw}'")
    return value


# Backward compatibility with Volume I
Config = Settings
load_config = load_settings
