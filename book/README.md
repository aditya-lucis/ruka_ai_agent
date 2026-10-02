# Ruka Coding Agent — Documentation Pack

Dokumen ini berisi rancangan dan instruksi untuk mengembangkan Ruka menjadi Coding Agent setara Claude Code, **dengan kepribadian & lore tetap utuh**.

## Isi Folder

| File | Keterangan | Rekomendasi Penempatan di Repo |
|------|----------|-------------------------------|
| `RUKA_Coding_Agent_Design.md` | Rancangan lengkap + kerangka class tool Phase 1 | `docs/RUKA_Coding_Agent_Design.md` atau root |
| `AGENTS.md` | Instruksi wajib untuk AI Coding Agent & kontributor | **Root repository** (`AGENTS.md`) |
| `GITHUB_ISSUES.md` | 12 issue GitHub siap copy-paste | `docs/GITHUB_ISSUES.md` |

## Cara Memasang ke Repository Ruka

### Opsi 1 — Paling Direkomendasikan

```bash
# Dari root repository ruka_ai_agent
cp AGENTS.md ./
mkdir -p docs
cp RUKA_Coding_Agent_Design.md docs/
cp GITHUB_ISSUES.md docs/
```

### Opsi 2 — Semua di dalam docs/

```bash
mkdir -p docs/coding-agent
cp *.md docs/coding-agent/
```

## Prioritas Setelah Memasukkan File

1. Letakkan `AGENTS.md` di **root** agar terbaca otomatis oleh Cursor / Windsurf / Claude Code / Antigravity.
2. Buat Milestone di GitHub: `Phase 1 - Foundation`, `Phase 2 - Agentic`, `Phase 3 - Polish`.
3. Copy-paste issue dari `GITHUB_ISSUES.md` ke GitHub Issues.
4. Mulai implementasi dari Issue #1 (`read_file`, `write_file`, dll).

---

**Catatan untuk AI Agent (Cursor / Antigravity / Claude / Gemini):**  
Baca `AGENTS.md` terlebih dahulu sebelum melakukan perubahan kode apa pun.
