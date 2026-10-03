# AGENTS.md — Ruka Development Constitution
**Versi:** 4.0  
**Tanggal:** 3 Oktober 2026  
**Status:** Wajib dibaca sebelum mengubah kode apa pun

---

## 0. Identitas & Tujuan Ganda

**Ruka** adalah *Local-First Expressive Agentic Companion*.

Tujuan pengembangan saat ini bersifat **ganda dan selaras**:

1. **Menstabilkan Ruka Agentic**  
   Membuat kemampuan coding agent setara atau mendekati Claude Code, dengan Action-First yang nyata, Skills yang terpanggil, dan persona Marquis of Trendamis yang utuh — **termasuk setelah di-install di desktop**.

2. **Mengembangkan PROJECT NOCTIS**  
   Menumbuhkan Ruka menjadi AI Companion Operating System penuh (visi di `book/SRS_PROJECT_NOCTIS` dan `book/SAD_PROJECT_NOCTIS`) tanpa merusak fondasi yang sedang distabilkan.

Ruka **bukan** salinan Claude Code.  
Ruka adalah Marquis yang menguasai rekayasa perangkat lunak dan sedang ditumbuhkan menjadi sistem kehadiran yang hidup.

**Dokumen acuan visi jangka panjang:**
- `book/SRS_PROJECT_NOCTIS` — Spesifikasi Kebutuhan
- `book/SAD_PROJECT_NOCTIS` — Analisis & Desain Sistem (OOAD + UML 2.5.1)
- `RUKA_NOCTIS_Alignment_Map.md` — Peta keselarasan Ruka ↔ Noctis

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
   Keputusan penting (routing, confidence, planning, self-correction, loop health) sedapat mungkin memiliki justifikasi matematis yang dapat diaudit.

6. **Jangan merusak fitur Companion**  
   Voice, Vision dasar, Memory, Desktop UI, dan System Tray harus tetap berfungsi.

7. **Production-ready adalah syarat selesai**  
   Fitur baru dianggap **belum selesai** sampai berfungsi di versi yang di-install (ruka-brain.exe + Electron Desktop), bukan hanya di mode development.

8. **Setiap langkah Ruka = batu bata Noctis**  
   Perubahan harus memperkuat Ruka hari ini **dan** menjadi fondasi yang sah bagi organ PROJECT NOCTIS. Jangan membangun yang bertentangan dengan SRS/SAD Noctis tanpa alasan kuat dan terdokumentasi.

---

## 2. Target Kapabilitas

### 2.1 Stabilisasi Ruka Agentic (Prioritas Utama Saat Ini)

| Kapabilitas | Target |
|-------------|--------|
| Real skill calling (bukan roleplay) | Wajib |
| Multi-file edit & refactor | Skills + Agentic Loop |
| Shell / terminal + PathJail | Stabil |
| Git (status, diff, commit, branch, log) | Perkuat |
| Project understanding (`repo_map`) | Perkuat |
| Test → fix → verify dasar | Harus ada |
| Production wiring (bundle, frozen path, brain↔gateway) | Wajib lulus checklist |

### 2.2 Diferensiasi (Wajib Dipertahankan)

| Area | Ciri Khas Ruka |
|------|----------------|
| Persona | Marquis of Trendamis yang konsisten |
| Presence | Desktop companion + Voice + Tray |
| Local-First | Zero-Trust, PathJail ketat |
| Mathematical Foundations | Score, Belief, calibration, loop health |
| Relationship | Memory jangka panjang dengan Young Lord |

### 2.3 Arah PROJECT NOCTIS (Kompas Jangka Panjang)

Organ Noctis dibangun secara bertahap di atas fondasi Ruka:

| Organ Noctis | Benih di Ruka Saat Ini |
|--------------|------------------------|
| Brain | `ruka_cognition` + Math Foundations + Agentic |
| Crimson Heart | Orchestrator + LoopGuard + SkillsRuntime |
| Shadow Hands | Skills (code_*, git_*, run_terminal) + PathJail + Confirmations |
| Memory Palace | Memory 3 lapis + RAG |
| Noctis OS / EventBus | Gateway + Electron + launcher |
| Converse / Voice | Chat path + TTS/ASR |
| Presence / Avatar / Eyes | Masih dini — jangan dikejar sebelum Fase A stabil |

Detail mapping: lihat `RUKA_NOCTIS_Alignment_Map.md`.

---

## 3. Arsitektur yang Harus Dipahami

```
Client (Desktop Electron / CLI)
        ↓
Ruka Gateway (Session • Events • Permissions • Skills Runtime)
        ↓
Cognitive Core (Intent → Planner → Agentic Loop → Expression)
        ↓
Skills Runtime + PathJail + Math Foundations
        ↓
Hasil nyata → Expression Layer (Persona Marquis) → Client
```

Ke depan, Gateway dievolusikan menjadi benih **EventBus V3** (namespace, publish-only) sesuai SAD Noctis, tanpa merusak jalur yang sudah jalan.

---

## 4. Mode Operasi

### 4.1 Mode Percakapan
- Persona penuh
- Fokus kehadiran dan hubungan

### 4.2 Mode Agentic (Coding / Command)
- **Action-First**
- Wajib memakai SkillsRuntime
- Dilarang mengarang tool call
- Hasil nyata dibungkus gaya Marquis
- Multi-step memakai Orchestrator + LoopGuard + Budget

---

## 5. Aturan Pengembangan

### 5.1 Menambah Kemampuan
- Utamakan **Skill** (`SKILL.md` + handler)
- Deklarasikan `risk_level` dan `permissions`
- Pastikan jalan di mode frozen (installed)
- Tanyakan: “Apakah ini batu bata Noctis yang sah?”

### 5.2 Mengubah Brain / Doctrine / Prompt
- Jangan melemahkan Action-First
- Jangan menghapus sapaan Young Lord / My Lord / Sir
- Jangan biarkan persona mengalahkan aksi

### 5.3 Mengubah Gateway / Skills
- PathJail dan Permission tetap gerbang
- Siapkan evolusi ke namespace EventBus (jangan hardcode panggilan silang organ)
- Brain harus menerima `skill_registry` dan `skills_runtime`

### 5.4 Standar Kode
- Python 3.10+ dengan type hints
- Docstring jelas
- Unit test untuk agentic path, skills, math, path resolution
- Tidak hardcode secret atau path non-portabel

---

## 6. Production Readiness (Syarat Selesai)

Fitur yang menyentuh Skills, Gateway, Agentic Mode, atau path resolution **belum selesai** sampai:

1. Skills ikut ter-bundle di `ruka-brain.exe`
2. Path benar di mode frozen (`sys._MEIPASS` + fallback)
3. Brain menerima `skill_registry` + `skills_runtime` dari Gateway
4. Diuji di versi **yang di-install** (Desktop + CLI global)
5. Tidak muncul teks palsu `[SYSTEM_CALL: ...]`
6. PathJail tidak mengunci user ke folder instalasi

Lihat: `RUKA_Production_Readiness_Checklist.md`

> “Sudah jalan di `python launcher.py`” **bukan** kriteria selesai.

---

## 7. Prioritas Pengembangan Saat Ini

### Urutan Wajib

1. **Stabilisasi Agentic Mode** — Action-First + real skill calling + production wiring  
2. **Production Readiness** — lulus checklist di versi installed  
3. **Git & Project Understanding** yang lebih dalam  
4. **Test → Fix → Verify** dasar  
5. **Evolusi Gateway** menuju EventBus ringan (namespace, publish-only)  
6. **Perluasan Memory** menuju benih Memory Palace (sayap relationship / project / preference)  
7. **Hands & Conversation depth** (setelah 1–4 stabil)  
8. **Presence / organ kehadiran** (jangan mendahului stabilisasi agentic)

Organ Noctis yang belum punya benih kuat (Avatar, Eyes penuh, Forge) **tidak** dikerjakan sebelum Fase stabilisasi selesai.

---

## 8. Yang Dilarang Keras

- Mematikan atau melemahkan persona Ruka
- Menulis teks palsu seolah-olah memanggil tool
- Melemahkan PathJail / Zero-Trust
- Menambah fitur yang hanya jalan di development
- Menganggap selesai tanpa uji di versi installed
- Membangun organ Noctis besar sambil membiarkan Agentic Mode masih roleplay
- Menyimpang dari SRS/SAD Noctis tanpa dokumentasi alasan
- Menyimpan secret di repository

---

## 9. Referensi Cepat

| Dokumen | Isi |
|---------|-----|
| `book/SRS_PROJECT_NOCTIS` | Spesifikasi kebutuhan PROJECT NOCTIS |
| `book/SAD_PROJECT_NOCTIS` | Analisis & desain sistem Noctis |
| `RUKA_NOCTIS_Alignment_Map.md` | Peta keselarasan Ruka ↔ Noctis |
| `RUKA_Claude_Code_Parity_Design.md` | Parity & differentiation vs Claude Code |
| `RUKA_Agentic_Mode_Design.md` | Rancangan Mode Agentic |
| `AGENTIC_MODE_IMPLEMENTATION.md` | Implementasi konkret |
| `RUKA_Production_Readiness_Checklist.md` | Checklist production |
| `RUKA_Gateway_Design.md` | Control plane |
| `RUKA_Skills_System_Design.md` | Sistem skills |
| `RUKA_Mathematical_Foundations.md` | Fondasi matematika |
| `docs/SKILL_SPEC.md` | Spesifikasi SKILL.md |

---

## 10. Penutup

Kita sedang mengerjakan dua hal yang saling menguatkan:

- **Ruka Agentic yang stabil dan tajam** — agar Young Lord punya companion coding yang benar-benar bertindak.
- **PROJECT NOCTIS yang tumbuh bertahap** — agar Ruka suatu hari menjadi kehadiran yang hidup, bukan hanya alat.

Keduanya hanya berhasil jika kita disiplin:

> Selesaikan yang sedang bernapas.  
> Jadikan setiap perbaikan batu bata Noctis.  
> Jangan pernah mengorbankan persona, safety, dan production-readiness.

Setiap baris kode harus bisa dipertanggungjawabkan di hadapan Young Lord — baik hari ini di desktopnya, maupun di masa depan sebagai organ sistem yang lebih besar.

---

**Dokumen ini wajib dihormati oleh setiap AI Coding Agent dan kontributor manusia.**

— Ruka Development Constitution v4.0  
*Marquis of Trendamis Development Council*  
*Menuju PROJECT NOCTIS*
