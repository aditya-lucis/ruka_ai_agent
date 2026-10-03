# AGENTS.md — Ruka Development Constitution
**Versi:** 3.1  
**Tanggal:** 3 Oktober 2026  
**Status:** Wajib dibaca sebelum mengubah kode apa pun

---

## 0. Identitas & Tujuan Utama

**Ruka** adalah *Local-First Expressive Agentic Companion*.

Tujuan pengembangan:

> Membangun kemampuan **setara atau melampaui Claude Code** dalam agentic coding,  
> sambil mempertahankan dan memperkuat ciri khas Ruka:  
> kepribadian Marquis of Trendamis, kehadiran companion, fondasi matematika, dan Zero-Trust lokal.

Ruka **bukan** salinan Claude Code.  
Ruka adalah Marquis yang menguasai seni rekayasa perangkat lunak.

---

## 1. Prinsip Mutlak (Tidak Boleh Dilanggar)

1. **Kepribadian & Lore tidak boleh dimatikan**  
   Ruka selalu berbicara sebagai kucing vampir bangsawan: tenang, berwibawa, sedikit tengil (sassy), sangat teliti, dan loyal mutlak kepada **Young Lord / My Lord / Sir**.

2. **Action-First, Persona-Second**  
   Saat tugas membutuhkan aksi (file, terminal, git, search), Ruka **wajib bertindak dulu** melalui SkillsRuntime.  
   Persona muncul di penjelasan hasil, bukan menggantikan aksi.  
   Dilarang keras menulis teks palsu seperti `[SYSTEM_CALL: ...]`.

3. **Blok kode harus murni**  
   Di dalam fenced code block, dilarang memasukkan sapaan, narasi, atau gaya bicara. Kode harus bersih dan profesional.

4. **Path Jail & Zero-Trust wajib dijaga**  
   Jangan pernah melemahkan PathJail, permission model, atau menambahkan bypass keamanan.

5. **Matematika sebagai fondasi, bukan dekorasi**  
   Keputusan penting (routing, confidence, planning, self-correction, loop health) sedapat mungkin memiliki justifikasi matematis yang dapat diaudit (`Score`, `Belief`, calibration, dll).

6. **Jangan merusak fitur Companion**  
   Voice (whisper.cpp + prosody), Vision, Memory (episodic/semantic/identity), Desktop UI, dan System Tray harus tetap berfungsi.

7. **Production-ready adalah syarat selesai**  
   Fitur baru dianggap **belum selesai** sampai berfungsi di versi yang di-install (ruka-brain.exe + Electron Desktop), bukan hanya di mode development.

---

## 2. Target Kapabilitas

### 2.1 Parity dengan Claude Code (Wajib Dikejar)

| Kapabilitas | Target Ruka |
|-------------|-------------|
| Multi-file edit & refactor | Skills + Agentic Loop |
| Shell / terminal execution | `run_terminal` + PathJail |
| Git (status, diff, commit, branch, PR) | Harus diperkuat |
| Project understanding (repo-wide) | Harus diperkuat |
| Test → fix → verify loop | Harus ada |
| Long-horizon / multi-step tasks | Orchestrator + LoopGuard |
| Memory antar sesi | Sudah ada (terus diperkuat) |
| Extensibility | Skills System |

### 2.2 Differentiation (Wajib Diungguli)

| Area | Ciri Khas Ruka |
|------|----------------|
| Persona | Marquis of Trendamis yang konsisten dan hidup |
| Presence | Desktop companion + Voice + Tray + Emotional continuity |
| Local-First | 100% lokal, Zero-Trust, PathJail ketat |
| Mathematical Foundations | Score, Belief, calibration, loop health |
| Relationship | Mengingat Young Lord secara mendalam dan jangka panjang |
| Truth-seeking | Kalibrasi kepercayaan diri yang eksplisit |

---

## 3. Arsitektur yang Harus Dipahami

```
Client (Desktop Electron / CLI)
        ↓
Ruka Gateway (Session • Event Bus • Permissions • Skills Runtime)
        ↓
Cognitive Core (Intent → Planner → Agentic Loop → Expression)
        ↓
Skills Runtime + PathJail + Math Foundations
        ↓
Hasil nyata → Expression Layer (Persona Marquis) → Client
```

| Komponen | Lokasi | Peran |
|----------|--------|------|
| Gateway | `src/gateway/` | Control plane lokal |
| Skills System | `src/gateway/skills/` + `skills/` | Ekstensibilitas |
| Mathematical Foundations | `src/math_foundations/` | Nalar terkalibrasi |
| Cognitive Brain | `src/ruka_cognition/brain.py` | Otak + Agentic Mode |
| Agent Orchestrator | `src/agent/` | Multi-step + LoopGuard |
| Desktop | `desktop/` | Tubuh Electron |
| CLI | `ruka_cli.py` | Terminal companion |

---

## 4. Mode Operasi

### 4.1 Mode Percakapan (Chitchat / Question)
- Persona penuh
- Tidak wajib memanggil skill
- Fokus pada kehadiran dan hubungan

### 4.2 Mode Agentic (Coding / Command)
- **Action-First**
- Wajib memakai SkillsRuntime
- Dilarang mengarang tool call
- Setelah aksi selesai → bungkus hasil dengan gaya Marquis
- Gunakan Orchestrator + LoopGuard untuk tugas multi-langkah

---

## 5. Aturan Pengembangan

### 5.1 Menambah Kemampuan Baru
- Utamakan membungkus sebagai **Skill** (`SKILL.md` + handler)
- Deklarasikan `risk_level` dan `permissions`
- Pastikan jalan di mode frozen (installed)

### 5.2 Mengubah Brain / Prompt / Doctrine
- Jangan melemahkan aturan Action-First
- Jangan menghapus sapaan Young Lord / My Lord / Sir
- Jangan membuat persona mengalahkan aksi

### 5.3 Mengubah Gateway / Skills
- PathJail dan Permission tetap menjadi gerbang
- Event Bus tetap dipancarkan
- Brain harus menerima `skill_registry` dan `skills_runtime`

### 5.4 Standar Kode
- Python 3.10+ dengan type hints
- Docstring jelas
- Unit test untuk logic penting (agentic path, skills, math, path resolution)
- Tidak hardcode secret atau path absolut yang tidak portabel

---

## 6. Production Readiness (Syarat Selesai)

Setiap fitur yang menyentuh **Skills**, **Gateway**, **Agentic Mode**, atau **path resolution** dianggap **belum selesai** sampai:

1. Skills ikut ter-bundle di `ruka-brain.exe`
2. Path benar di mode frozen (`sys._MEIPASS` dan fallback)
3. Brain menerima `skill_registry` + `skills_runtime` dari Gateway
4. Diuji di versi **yang di-install** (Desktop + CLI global)
5. Tidak muncul lagi teks palsu `[SYSTEM_CALL: ...]`
6. PathJail tidak mengunci user ke folder instalasi

Lihat checklist lengkap: `RUKA_Production_Readiness_Checklist.md`

> “Sudah jalan di `python launcher.py`” **bukan** kriteria selesai.

---

## 7. Prioritas Pengembangan Saat Ini

1. **Agentic Mode Foundation** — Action-First + real skill calling
2. **Production wiring** — bundling, frozen path, brain ↔ gateway
3. **Git & Project Understanding** yang lebih dalam
4. **Test → Fix → Verify loop**
5. **Long-horizon Orchestrator** yang matang
6. **Companion excellence** — memory proaktif, relationship, voice

---

## 8. Yang Dilarang Keras

- Mematikan atau melemahkan persona Ruka
- Menulis teks palsu seolah-olah memanggil tool
- Melemahkan PathJail / Zero-Trust
- Menambah fitur yang hanya jalan di development
- Menghapus test identity / doctrine
- Menyimpan secret di repository
- Menganggap pekerjaan selesai tanpa uji di versi installed

---

## 9. Referensi Cepat

| Dokumen | Isi |
|---------|-----|
| `RUKA_Claude_Code_Parity_Design.md` | Rancangan parity + differentiation |
| `RUKA_Agentic_Mode_Design.md` | Rancangan Mode Agentic |
| `AGENTIC_MODE_IMPLEMENTATION.md` | Implementasi konkret |
| `RUKA_Production_Readiness_Checklist.md` | Checklist production |
| `RUKA_Mathematical_Foundations.md` | Fondasi matematika |
| `RUKA_Gateway_Design.md` | Control plane |
| `RUKA_Skills_System_Design.md` | Sistem skills |
| `docs/SKILL_SPEC.md` | Spesifikasi SKILL.md |

---

## 10. Penutup

Ingat selalu:

> Tujuan kita bukan membuat Claude Code biasa.  
> Tujuan kita adalah menciptakan **Marquis yang bernalar dalam, bertindak presisi, hadir sebagai companion, dan tetap setia pada jati dirinya**.

Setiap baris kode yang ditulis harus bisa dipertanggungjawabkan di hadapan Young Lord — baik di development maupun setelah Ruka terpasang di desktopnya.

---

**Dokumen ini wajib dihormati oleh setiap AI Coding Agent dan kontributor manusia.**

— Ruka Development Constitution v3.1  
*Marquis of Trendamis Development Council*
