# -*- coding: utf-8 -*-
"""RUKA Skills System — Skill Loader & Frontmatter Parser.

Membaca dan memvalidasi berkas SKILL.md dari direktori skills,
mengekstrak metadata YAML frontmatter, serta memuat objek Skill.
"""
from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import Any

from src.gateway.skills.models import Skill

log = logging.getLogger("ruka.gateway.skills.loader")

VALID_RISK_LEVELS = {"low", "medium", "high", "critical"}


def parse_yaml_frontmatter(text: str) -> tuple[dict[str, Any], str]:
    """Mengekstrak frontmatter YAML dan badan Markdown dari teks berkas SKILL.md.

    Returns:
        tuple (metadata_dict, body_markdown)
    """
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return {}, text

    yaml_lines: list[str] = []
    body_lines: list[str] = []
    in_frontmatter = True
    found_end = False

    for line in lines[1:]:
        if in_frontmatter:
            if line.strip() == "---":
                in_frontmatter = False
                found_end = True
                continue
            yaml_lines.append(line)
        else:
            body_lines.append(line)

    if not found_end:
        return {}, text

    metadata = _parse_simple_yaml("\n".join(yaml_lines))
    body = "\n".join(body_lines).strip()
    return metadata, body


def _parse_simple_yaml(yaml_text: str) -> dict[str, Any]:
    """Parser YAML ringan dan mandiri (tanpa dependensi eksternal)
    yang mendukung string, angka, boolean, list inline/multiline, dan blok literal |.
    """
    data: dict[str, Any] = {}
    lines = yaml_text.splitlines()
    i = 0
    n = len(lines)

    current_key: str | None = None

    while i < n:
        raw_line = lines[i]
        line = raw_line.strip()
        i += 1

        if not line or line.startswith("#"):
            continue

        # Multiline list item under current_key
        if line.startswith("- ") and current_key is not None:
            val = line[2:].strip().strip("'\"")
            if not isinstance(data.get(current_key), list):
                data[current_key] = []
            data[current_key].append(_convert_val(val))
            continue

        if ":" not in line:
            continue

        key, _, val = line.partition(":")
        key = key.strip()
        val = val.strip()
        current_key = key

        # Multiline block scalar (|)
        if val == "|":
            block_lines: list[str] = []
            while i < n:
                next_line = lines[i]
                # Indented line is part of block
                if next_line.startswith("  ") or next_line.startswith("\t"):
                    block_lines.append(next_line.strip())
                    i += 1
                elif not next_line.strip():
                    block_lines.append("")
                    i += 1
                else:
                    break
            data[key] = "\n".join(block_lines).strip()
            continue

        # Inline list [a, b, c]
        if val.startswith("[") and val.endswith("]"):
            inner = val[1:-1].strip()
            if not inner:
                data[key] = []
            else:
                items = [item.strip().strip("'\"") for item in inner.split(",")]
                data[key] = [_convert_val(it) for it in items if it]
            continue

        if val:
            data[key] = _convert_val(val)
        else:
            # Maybe a multiline list follows
            data[key] = []

    return data


def _convert_val(v: str) -> Any:
    cleaned = v.strip().strip("'\"")
    low = cleaned.lower()
    if low == "true":
        return True
    if low == "false":
        return False
    if low in ("null", "none"):
        return None
    try:
        if "." in cleaned:
            return float(cleaned)
        return int(cleaned)
    except ValueError:
        return cleaned


class SkillLoader:
    """Pemuat dan validator berkas spesifikasi SKILL.md."""

    def load_skill_from_path(self, skill_dir: Path | str) -> Skill:
        """Memuat skill dari direktori yang memuat SKILL.md."""
        p = Path(skill_dir).resolve()
        skill_file = p / "SKILL.md"
        if not skill_file.exists():
            raise FileNotFoundError(f"Berkas SKILL.md tidak ditemukan di: {p}")

        content = skill_file.read_text(encoding="utf-8", errors="replace")
        meta, body = parse_yaml_frontmatter(content)

        # Validasi field wajib
        missing_fields = []
        for req in ("name", "version", "description", "risk_level", "permissions"):
            if req not in meta or not meta[req]:
                missing_fields.append(req)

        if missing_fields:
            raise ValueError(f"SKILL.md di {p} tidak memiliki field wajib: {missing_fields}")

        risk = str(meta["risk_level"]).lower().strip()
        if risk not in VALID_RISK_LEVELS:
            raise ValueError(f"risk_level '{risk}' tidak valid. Harus salah satu dari: {VALID_RISK_LEVELS}")

        perms = meta["permissions"]
        if isinstance(perms, str):
            perms = [perms]

        tags = meta.get("tags", [])
        if isinstance(tags, str):
            tags = [tags]

        return Skill(
            name=str(meta["name"]).strip(),
            version=str(meta["version"]).strip(),
            description=str(meta["description"]).strip(),
            author=str(meta.get("author", "Ruka Core Team")).strip(),
            license=str(meta.get("license", "MIT")).strip(),
            tags=tags,
            risk_level=risk,
            requires_confirmation=bool(meta.get("requires_confirmation", False)),
            permissions=perms,
            entry_point=meta.get("entry_point"),
            timeout_seconds=float(meta.get("timeout_seconds", 30.0)),
            instructions_md=body,
            folder_path=p,
        )

    def discover_skills(self, directory: Path | str) -> list[Skill]:
        """Memindai seluruh subfolder pada sebuah direktori untuk menemukan skills valid."""
        base = Path(directory).resolve()
        if not base.exists() or not base.is_dir():
            return []

        loaded: list[Skill] = []
        for child in base.iterdir():
            if child.is_dir() and (child / "SKILL.md").exists():
                try:
                    skill = self.load_skill_from_path(child)
                    loaded.append(skill)
                except Exception as ex:
                    log.warning("Gagal memuat skill di %s: %s", child, ex)

        return loaded
