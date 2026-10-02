# -*- coding: utf-8 -*-
"""Project Memory: Lapisan ingatan khusus per-proyek / repositori (Phase 2).
Menyimpan konvensi, arsitektur, daftar batasan ('jangan lakukan ini'),
serta preferensi rekayasa perangkat lunak Young Lord.
"""
from __future__ import annotations

import json
import logging
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from src.memory.models import MemoryKind, MemoryRecord

log = logging.getLogger("ruka.agent.project_memory")


@dataclass
class ArchitectureDecision:
    title: str
    decision: str
    recorded_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )


class ProjectMemory:
    """Ingatan jangka panjang per-repositori / proyek untuk mode koding."""

    def __init__(
        self,
        project_root: str | Path | None = None,
        *,
        conventions: list[str] | None = None,
        architecture_decisions: list[ArchitectureDecision] | None = None,
        constraints: list[str] | None = None,
        coding_style: list[str] | None = None,
    ):
        self.project_root = Path(project_root).resolve() if project_root else Path.cwd()
        self.conventions: list[str] = conventions or []
        self.architecture_decisions: list[ArchitectureDecision] = architecture_decisions or []
        self.constraints: list[str] = constraints or []
        self.coding_style: list[str] = coding_style or []

    def add_convention(self, convention: str) -> None:
        c = convention.strip()
        if c and c not in self.conventions:
            self.conventions.append(c)

    def add_architecture_decision(self, title: str, decision: str) -> None:
        t = title.strip()
        d = decision.strip()
        if t and d:
            self.architecture_decisions.append(
                ArchitectureDecision(title=t, decision=d)
            )

    def add_constraint(self, rule: str) -> None:
        """Menambahkan larangan / batasan keras ('jangan lakukan ini')."""
        r = rule.strip()
        if r and r not in self.constraints:
            self.constraints.append(r)

    def add_coding_style(self, style: str) -> None:
        s = style.strip()
        if s and s not in self.coding_style:
            self.coding_style.append(s)

    def format_prompt_context(self) -> str:
        """Format blok ringkas untuk disematkan pada system prompt kognisi."""
        sections: list[str] = []

        if self.conventions:
            items = "\n".join(f"  • {c}" for c in self.conventions)
            sections.append(f"Konvensi Proyek:\n{items}")

        if self.coding_style:
            items = "\n".join(f"  • {s}" for s in self.coding_style)
            sections.append(f"Gaya Koding Young Lord:\n{items}")

        if self.constraints:
            items = "\n".join(f"  • [DILARANG] {c}" for c in self.constraints)
            sections.append(f"Batasan Mutlak ('Jangan Lakukan Ini'):\n{items}")

        if self.architecture_decisions:
            items = "\n".join(
                f"  • [{a.title}]: {a.decision}" for a in self.architecture_decisions[-5:]
            )
            sections.append(f"Keputusan Arsitektur Terakhir:\n{items}")

        if not sections:
            return ""

        return "=== INGATAN PROYEK (PROJECT MEMORY) ===\n" + "\n\n".join(sections)

    def save_to_workspace(self, workspace_path: str | Path | None = None) -> Path:
        """Menyimpan Project Memory ke direktori .ruka/project_memory.json di workspace."""
        ws = Path(workspace_path).resolve() if workspace_path else self.project_root
        target_dir = ws / ".ruka"
        target_dir.mkdir(parents=True, exist_ok=True)
        file_path = target_dir / "project_memory.json"

        data = {
            "project_root": str(ws),
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "conventions": self.conventions,
            "coding_style": self.coding_style,
            "constraints": self.constraints,
            "architecture_decisions": [asdict(a) for a in self.architecture_decisions],
        }
        file_path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
        log.info("project memory disimpan ke %s", file_path)
        return file_path

    @classmethod
    def load_from_workspace(cls, workspace_path: str | Path | None = None) -> "ProjectMemory":
        """Memuat Project Memory dari .ruka/project_memory.json."""
        ws = Path(workspace_path).resolve() if workspace_path else Path.cwd()
        file_path = ws / ".ruka" / "project_memory.json"

        if not file_path.exists():
            return cls(project_root=ws)

        try:
            data = json.loads(file_path.read_text(encoding="utf-8"))
            decisions = [
                ArchitectureDecision(
                    title=item["title"],
                    decision=item["decision"],
                    recorded_at=item.get("recorded_at", ""),
                )
                for item in data.get("architecture_decisions", [])
            ]
            return cls(
                project_root=ws,
                conventions=data.get("conventions", []),
                architecture_decisions=decisions,
                constraints=data.get("constraints", []),
                coding_style=data.get("coding_style", []),
            )
        except Exception as e:
            log.warning("gagal membaca %s: %s, gunakan memori baru", file_path, e)
            return cls(project_root=ws)

    def export_to_memory_records(self, user_id: str = "young_lord") -> list[MemoryRecord]:
        """Ekspor entri memori proyek ke objek MemoryRecord (MemoryKind.PROJECT)."""
        records: list[MemoryRecord] = []
        now = datetime.now(timezone.utc)

        for c in self.conventions:
            records.append(
                MemoryRecord(
                    id=f"{user_id}:proj_conv:{hash(c) & 0xffffffff}",
                    kind=MemoryKind.PROJECT,
                    content=f"[Konvensi] {c}",
                    user_id=user_id,
                    importance=0.7,
                    created_at=now,
                )
            )

        for r in self.constraints:
            records.append(
                MemoryRecord(
                    id=f"{user_id}:proj_rule:{hash(r) & 0xffffffff}",
                    kind=MemoryKind.PROJECT,
                    content=f"[Batasan] {r}",
                    user_id=user_id,
                    importance=0.9,
                    created_at=now,
                )
            )

        return records
