# -*- coding: utf-8 -*-
"""Unit tests for src.gateway.skills package.
Memverifikasi SkillLoader, SkillRegistry, SkillsRuntime,
penegakan keamanan (Permissions & PathJail), serta coding_bridge.
"""
from pathlib import Path
import pytest

from src.gateway.skills.models import Skill, SkillExecutionResult
from src.gateway.skills.loader import SkillLoader, parse_yaml_frontmatter
from src.gateway.skills.registry import SkillRegistry
from src.gateway.skills.runtime import SkillsRuntime
from src.gateway.skills.coding_bridge import register_builtin_coding_skills
from src.gateway.permissions import PermissionManager, RiskLevel
from src.gateway.events import EventBus


class TestSkillLoader:
    def test_parse_frontmatter_valid(self):
        text = """---
name: sample_skill
version: 1.0.0
description: Deskripsi singkat
risk_level: low
tags: [test, sample]
permissions:
  - filesystem:read
---
# Instruksi Skill
Ini instruksinya.
"""
        meta, body = parse_yaml_frontmatter(text)
        assert meta["name"] == "sample_skill"
        assert meta["version"] == "1.0.0"
        assert meta["risk_level"] == "low"
        assert meta["tags"] == ["test", "sample"]
        assert meta["permissions"] == ["filesystem:read"]
        assert "Ini instruksinya." in body

    def test_loader_validation(self, tmp_path):
        loader = SkillLoader()
        s_dir = tmp_path / "test_skill"
        s_dir.mkdir()
        (s_dir / "SKILL.md").write_text("""---
name: my_skill
version: 0.1.0
description: Skill uji coba
risk_level: medium
permissions:
  - filesystem:read
---
Konten instruksi.
""", encoding="utf-8")

        skill = loader.load_skill_from_path(s_dir)
        assert skill.name == "my_skill"
        assert skill.risk_level == "medium"
        assert skill.permissions == ["filesystem:read"]

    def test_loader_missing_mandatory_fields(self, tmp_path):
        loader = SkillLoader()
        s_dir = tmp_path / "broken_skill"
        s_dir.mkdir()
        (s_dir / "SKILL.md").write_text("""---
name: broken
---
Bad skill
""", encoding="utf-8")

        with pytest.raises(ValueError, match="tidak memiliki field wajib"):
            loader.load_skill_from_path(s_dir)


class TestSkillRegistry:
    def test_registry_lifecycle(self):
        reg = SkillRegistry()
        s1 = Skill(name="s1", version="1.0", description="First skill", tags=["a", "b"], risk_level="low", permissions=[])
        s2 = Skill(name="s2", version="1.0", description="Second skill", tags=["b", "c"], risk_level="high", permissions=[])

        reg.register(s1)
        reg.register(s2)

        assert reg.get("s1") == s1
        assert len(reg.list()) == 2
        assert len(reg.list(tag="a")) == 1
        assert len(reg.list(tag="b")) == 2

        results = reg.search("First")
        assert len(results) == 1
        assert results[0].name == "s1"

        tools_def = reg.to_tool_definitions()
        assert len(tools_def) == 2
        assert tools_def[0]["name"] in ("s1", "s2")


class TestSkillsRuntimeSecurity:
    def test_execute_success(self, tmp_path):
        pm = PermissionManager(workspace_root=tmp_path)
        eb = EventBus()
        reg = SkillRegistry()
        runtime = SkillsRuntime(registry=reg, permission_manager=pm, event_bus=eb)

        s = Skill(
            name="echo",
            version="1.0",
            description="Echoes input",
            risk_level="low",
            permissions=["filesystem:read"],
            handler=lambda text: f"echo: {text}",
        )
        reg.register(s)

        res = runtime.execute("echo", args={"text": "Hello Young Lord"})
        assert res.success is True
        assert res.data == "echo: Hello Young Lord"
        assert len(eb.history(event_type="skill.executed")) == 1

    def test_execute_risk_confirmation(self, tmp_path):
        pm = PermissionManager(workspace_root=tmp_path)
        eb = EventBus()
        reg = SkillRegistry()
        runtime = SkillsRuntime(registry=reg, permission_manager=pm, event_bus=eb)

        critical_skill = Skill(
            name="wipe_db",
            version="1.0",
            description="Dangerous wipe",
            risk_level="critical",
            permissions=["filesystem:write"],
            handler=lambda: "wiped",
        )
        reg.register(critical_skill)

        # 1. Tanpa konfirmasi -> Gagal
        res1 = runtime.execute("wipe_db", args={}, confirm_granted=False)
        assert res1.success is False
        assert "membutuhkan konfirmasi eksplisit" in res1.error

        # 2. Dengan konfirmasi -> Sukses
        res2 = runtime.execute("wipe_db", args={}, confirm_granted=True)
        assert res2.success is True
        assert res2.data == "wiped"

    def test_path_jail_confinement(self, tmp_path):
        pm = PermissionManager(workspace_root=tmp_path)
        reg = SkillRegistry()
        runtime = SkillsRuntime(registry=reg, permission_manager=pm)

        skill = Skill(
            name="read_target",
            version="1.0",
            description="Reads path",
            risk_level="low",
            permissions=["filesystem:read"],
            handler=lambda path: path,
        )
        reg.register(skill)

        # Coba traversal ke luar workspace
        res = runtime.execute("read_target", args={"path": "../../outside_secret.txt"})
        assert res.success is False
        assert "Pelanggaran Path Jail" in res.error


class TestCodingBridge:
    def test_register_and_execute_coding_tools(self, tmp_path):
        pm = PermissionManager(workspace_root=tmp_path)
        reg = SkillRegistry()
        runtime = SkillsRuntime(registry=reg, permission_manager=pm)

        register_builtin_coding_skills(reg, workspace_root=tmp_path)

        assert reg.get("code_write") is not None
        assert reg.get("code_read") is not None
        assert reg.get("code_edit") is not None

        # Tulis berkas menggunakan skill code_write
        res_write = runtime.execute("code_write", args={"path": "hello.txt", "content": "Line 1\nLine 2\nLine 3\n"})
        assert res_write.success is True

        # Baca berkas menggunakan skill code_read
        res_read = runtime.execute("code_read", args={"path": "hello.txt"})
        assert res_read.success is True
        assert "Line 2" in res_read.data["content"]

        # Edit berkas menggunakan skill code_edit
        res_edit = runtime.execute("code_edit", args={"path": "hello.txt", "old_string": "Line 2", "new_string": "Line Modified"})
        assert res_edit.success is True

        # Pastikan berkas berubah
        res_check = runtime.execute("code_read", args={"path": "hello.txt"})
        assert "Line Modified" in res_check.data["content"]
