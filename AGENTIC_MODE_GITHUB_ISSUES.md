# GitHub Issues — RUKA Agentic Mode

Siap copy-paste ke GitHub Issues.

---

## Issue #1 — Foundation

**Title:**  
`feat(agentic): implement Action-First Agentic Mode with personality lock`

**Labels:** `enhancement`, `agentic`, `high-priority`

**Body:**

```markdown
## Summary
Implement Mode Agentic agar Ruka **benar-benar memanggil SkillsRuntime** saat mendapat tugas coding/command, sambil tetap mempertahankan kepribadian Marquis of Trendamis.

## Problem
Saat ini ketika Young Lord memberi perintah coding (baca file, ls, edit, dll):
- Ruka hanya roleplay panjang
- Menulis teks palsu seperti `[SYSTEM_CALL: list_directory(...)]`
- Meminta user menempelkan output terminal
- SkillsRuntime tidak pernah dipanggil di jalur CLI

## Root Cause
Jalur `ruka:chat-send` → `brain.think_and_reply()` tidak pernah masuk ke SkillsRuntime. Skill hanya diceritakan di dalam prompt.

## Solution
1. Tambah aturan keras **Mode Agentic** di Doctrine
2. Pecah `think_and_reply` menjadi:
   - Mode percakapan biasa (persona penuh)
   - Mode Agentic (`_agentic_execute`)
3. Implementasi:
   - `_is_agentic_request()`
   - `_agentic_execute()`
   - `_make_simple_plan()`
   - `_wrap_agentic_result()`
4. Prinsip: **Action-First, Persona-Second**

## Acceptance Criteria
- [ ] Perintah seperti "baca package.json" atau "lihat isi folder" benar-benar memanggil skill
- [ ] Tidak lagi muncul teks `[SYSTEM_CALL: ...]`
- [ ] Jawaban akhir tetap bergaya Marquis (tenang, berwibawa, sapaan Young Lord)
- [ ] PathJail dan permission tetap aktif
- [ ] Mode chitchat / obrolan biasa tidak rusak
- [ ] Ada fallback yang elegan jika SkillsRuntime belum tersedia

## References
- `docs/RUKA_Agentic_Mode_Design.md`
- `AGENTIC_MODE_IMPLEMENTATION.md`
```

---

## Issue #2 — Orchestrator Integration

**Title:**  
`feat(agentic): integrate AgentOrchestrator + LoopGuard into Agentic Mode`

**Labels:** `enhancement`, `agentic`

**Body:**

```markdown
## Summary
Ganti simple rule-based planner dengan `AgentOrchestrator` yang sudah ada agar mendukung multi-step reasoning, self-correction, dan perlindungan LoopGuard.

## Motivation
Simple planner hanya cukup untuk 1-2 langkah. Tugas coding nyata butuh iterasi (baca → pikir → edit → test → perbaiki).

## Acceptance Criteria
- [ ] Multi-step task dapat diselesaikan dalam satu sesi
- [ ] LoopGuard membatasi iterasi dan mendeteksi loop
- [ ] Hasil akhir tetap dibungkus Expression Layer (persona Marquis)
- [ ] Budget / token control dari Math Foundations digunakan
```

---

## Issue #3 — Better Planning & Intent

**Title:**  
`feat(agentic): improve intent detection and skill planning quality`

**Labels:** `enhancement`, `agentic`, `intelligence`

**Body:**

```markdown
## Summary
Perkuat deteksi intent coding/command dan tingkatkan kualitas pemilihan skill.

## Tasks
- Perluas keyword & pola di `NeuralIntentRouter`
- Tingkatkan `_make_simple_plan` atau ganti dengan hybrid (rule + LLM)
- Pertimbangkan skill composition (satu skill memanggil skill lain)

## Acceptance Criteria
- [ ] Intent coding lebih akurat (lebih sedikit false negative)
- [ ] Skill yang dipilih lebih tepat
- [ ] Mengurangi kasus "tidak ada skill yang cocok"
```

---

## Issue #4 — Safety & Confirmation

**Title:**  
`feat(agentic): tighten confirmation flow for dangerous skills`

**Labels:** `security`, `agentic`

**Body:**

```markdown
## Summary
Saat ini `confirm_granted=True` digunakan untuk memudahkan testing. Perlu diperketat kembali untuk skill berisiko tinggi (write, delete, shell berbahaya).

## Acceptance Criteria
- [ ] Skill dengan `risk_level: high` atau `requires_confirmation: true` meminta izin Young Lord
- [ ] Alur konfirmasi tetap bergaya Marquis (hormat dan jelas)
- [ ] PathJail tidak pernah dibypass
```

---

## Issue #5 — LLM-Driven Dynamic Tool Calling & ReAct Engine

**Title:** `feat(agentic): replace regex planning with LLM dynamic function calling and ReAct loop`  
**Labels:** `enhancement`, `agentic`, `high-priority`, `claude-code-parity`

**Body:**

```markdown
## Summary
Mengganti mekanisme perencanaan berbasis regex (`_make_simple_plan` & `_AGENTIC_PATTERNS`) dengan LLM-Driven Dynamic Function Calling berbasis JSON Schema untuk seluruh 11 skill Gateway, mengeliminasi halusinasi dan kegagalan klasifikasi input alami.

## Motivation & Problem
Saat ini Ruka mengandalkan regex pencocokan string untuk menentukan apakah sebuah perintah membutuhkan tool dan tool mana yang dipanggil. Jika user menggunakan variasi bahasa manusia ("coba cek ada apa aja di folder ini"), regex gagal cocok dan Ruka jatuh ke mode chat biasa sehingga LLM berhalusinasi mengarang berkas fiktif.

## Tasks
1. Deklarasikan JSON Schema formal untuk seluruh 11 skill Gateway (`list_dir`, `code_read`, `code_write`, `code_edit`, `code_search`, `run_terminal`, `git_status`, `git_diff`, `git_log`, `git_commit`, `repo_map`).
2. Implementasikan Controller ReAct di `src/agent/react_controller.py`:
   - Memberikan tools schema ke LLM
   - Parsing structured function calls dari respon model
   - Mengeksekusi tool via `SkillsRuntime`
   - Mengumpankan kembali hasil tool sebagai observasi ke giliran berikutnya sampai `final_answer` tercapai
3. Jadikan ReAct Controller sebagai alur utama pada setiap sesi coding/command, dengan regex sederhana hanya sebagai fallback darurat saat LLM offline.

## Acceptance Criteria
- [ ] Pertanyaan bebas manusia tentang berkas/folder/git ("ada apa di sini", "cek folder ini", "apakah kosong") otomatis memicu pemanggilan tool nyata.
- [ ] Tidak ada lagi halusinasi berkas fiktif (seperti `README.md` atau `src/engine.py` pada direktori kosong).
- [ ] Model mampu memanggil lebih dari satu tool secara berurutan untuk menyelesaikan instruksi kompleks.
- [ ] Unit test mencakup evaluasi multi-turn tool calling dengan mock LLM.
```

---

## Issue #6 — Claude Code-Caliber Terminal UI & Inline Confirmation

**Title:** `feat(cli): elevate terminal UX to Claude Code caliber with live spinners and inline interactive confirmation`  
**Labels:** `cli`, `ux`, `claude-code-parity`, `enhancement`

**Body:**

```markdown
## Summary
Merombak antarmuka `ruka_cli.py` agar memiliki standar estetika dan interaktivitas setara Claude Code: status bar sesi lengkap, animasi live spinner, indikator hierarki langkah eksekusi, serta alur konfirmasi persetujuan interaktif langsung (*inline prompt*).

## Tasks
1. **Aristocratic Session Header & Status Bar**:
   - Tampilkan lokasi workspace aktif, status git branch/cleanliness, model kognisi aktif, dan indikator Zero-Trust Sandbox.
2. **Live Step & Activity Indicators**:
   - Tampilkan spinner saat LLM sedang berpikir (`⠋ Menelaah instruksi...`).
   - Tampilkan icon status langkah selesai: `✔ list_dir . (direktori kosong)`, `✔ code_write main.go (72 bytes)`.
3. **Inline Interactive Confirmation Prompt**:
   - Untuk aksi mutasi (`code_write`, `code_edit`, `run_terminal`), CLI langsung berhenti sejenak dan meminta input inline:
     `Izinkan aksi 'code_write' pada 'main.go'? [y]a / [t]olak / [d]iff / [s]elalu: `
   - Kirim respon persetujuan langsung ke IPC Gateway tanpa memutus sesi REPL.
4. **Syntax-Highlighted Unified Diff Viewer**:
   - Menampilkan preview perubahan kode berwarna hijau (+) dan merah (-) di dalam kotak border ANSI yang rapi sebelum disetujui.

## Acceptance Criteria
- [ ] User tidak perlu lagi mengetik tiket ID atau membalas chat terpisah untuk memberikan persetujuan berkas.
- [ ] Terminal terasa hidup, responsif, dan memberikan feedback visual langsung atas setiap tool yang sedang berjalan.
- [ ] Tampilan konsisten di Windows PowerShell, Command Prompt, dan Git Bash (MSYS2).
```

---

## Issue #7 — Autonomous Test-Fix-Verify & Self-Correction Loop

**Title:** `feat(agentic): integrate autonomous Test-Fix-Verify self-correction loop`  
**Labels:** `agentic`, `testing`, `autonomy`, `claude-code-parity`

**Body:**

```markdown
## Summary
Mengintegrasikan modul `src/agent/test_fix_verify.py` ke dalam alur kognisi utama Ruka, memungkinkan Ruka menulis kode, menjalankan unit test di terminal, menangkap error, memperbaiki kode secara mandiri, dan memverifikasi hingga seluruh test lulus.

## Tasks
1. Hubungkan `TestFixVerifyLoop` dengan session handler Gateway.
2. Dukung runner pengujian populer: `pytest` (Python), `go test` (Go), `npm test` / `vitest` / `jest` (TypeScript/JavaScript), `cargo test` (Rust).
3. Parser output pengujian otomatis: mengekstrak file, nomor baris, nama fungsi yang gagal, dan traceback error.
4. Terapkan LoopGuard dan batas maksimum percobaan self-correction (maksimal 3-5 iterasi) berlandaskan `src/math_foundations/control.py`.

## Acceptance Criteria
- [ ] Instruksi "perbaiki test yang gagal di modul X" mampu berjalan mandiri: jalankan test → deteksi error → edit berkas → jalankan ulang test → konfirmasi lulus.
- [ ] Jika perbaikan gagal mencapai status lulus dalam batas iterasi, agen berhenti secara elegan dan melaporkan analisis kegagalan kepada Young Lord.
```

---

## Issue #8 — Whole-Repo Intelligence & Coordinated Multi-File Refactoring

**Title:** `feat(intelligence): implement whole-repository mapping and coordinated multi-file refactoring`  
**Labels:** `intelligence`, `skills`, `git`, `claude-code-parity`

**Body:**

```markdown
## Summary
Meningkatkan pemahaman repositori Ruka agar setara dengan Claude Code melalui pemetaan pohon arsitektur (`repo_map`), indeks simbol, dan kemampuan refactoring atomik di banyak berkas sekaligus.

## Tasks
1. Optimalkan skill `repo_map` untuk menghasilkan ringkasan arsitektur terkompresi yang muat dalam context window.
2. Tambahkan pelacakan dependensi antar-berkas sederhana (import graph) agar perubahan nama fungsi atau signature API di berkas A otomatis merencanakan pembaruan di berkas B.
3. Transaksional Multi-File Edit: jika salah satu edit di rangkaian multi-file gagal karena PathJail atau sintaks tidak valid, sediakan opsi rollback bersih.
4. Git auto-commit helper: tawarkan pembuatan commit git atomik dengan pesan konvensional setelah refactor tuntas diverifikasi.

## Acceptance Criteria
- [ ] Ruka dapat menjelaskan struktur proyek skala menengah hanya dengan memanggil `repo_map`.
- [ ] Perubahan fungsi/tipe data yang dipakai di beberapa berkas dapat diselesaikan dalam satu siklus agentic.
```

---

## Issue #9 — Multi-Modal Coexistence & Production Packaging Verification

**Title:** `test(production): verify multi-modal companion coexistence and standalone installer integrity`  
**Labels:** `production`, `installer`, `multimodal`, `qa`

**Body:**

```markdown
## Summary
Memastikan bahwa peningkatan kapabilitas coding agent tidak mengorbankan atau merusak fitur multi-modal companion Ruka (suara whisper.cpp, vision, memory episodik SQLite, dan integrasi desktop Electron).

## Tasks
1. Verifikasi integrasi biner: `ruka-brain.exe` mandiri mengemas seluruh dependencies kognisi dan coding tanpa ketergantungan Python sistem.
2. Uji integrasi desktop: UI Electron menampilkan event coding bus (log aktivitas tool) bersamaan dengan avatar dan audio wicara.
3. Uji mode suara: memastikan transkripsi `whisper.cpp` dan sintesis respons Marquis tetap berfungsi normal saat dipanggil lewat Desktop.
4. Bangun installer rilis `Ruka Setup 0.3.x.exe` dan validasi instalasi bersih di mesin uji.

## Acceptance Criteria
- [ ] `ruka-brain.exe` berjalan mulus baik saat diluncurkan oleh Electron Desktop maupun CLI terminal.
- [ ] Memory percakapan dan preferensi Young Lord di `ruka.db` tetap terpelihara antar sesi.
- [ ] Seluruh suite unit test (560+ test) lulus 100%.
```

---

**Cara pakai:**  
Copy masing-masing blok di atas lalu buat Issue baru di repository GitHub Ruka.
