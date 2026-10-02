# GitHub Issues Ready — Ruka Coding Agent

Salin-tempel issue di bawah ini satu per satu ke repository GitHub.  
Semua issue sudah dilengkapi dengan label yang disarankan, acceptance criteria, dan referensi ke dokumen rancangan.

---

## Issue #1 — [Phase 1] Implement Core File Tools (`read_file`, `read_files`, `write_file`) [COMPLETED]

**Labels:** `enhancement`, `phase-1`, `tools`, `priority:high`  
**Status:** Completed & Tested (12/12 Phase 1 Unit Tests Passing)

### Deskripsi
Implementasikan tool dasar untuk membaca dan menulis file agar Ruka dapat berinteraksi dengan codebase.

### Acceptance Criteria
- [x] Tool `read_file` mendukung pembacaan penuh dan berdasarkan rentang baris (`start_line`, `end_line`)
- [x] Tool `read_files` mendukung pembacaan batch dengan batasan total karakter
- [x] Tool `write_file` dapat membuat file baru atau menimpa file yang sudah ada
- [x] Semua tool mematuhi Path Jail yang sudah ada
- [x] Terdaftar dengan benar di `ToolRegistry`
- [x] Memiliki type hints dan docstring yang jelas
- [x] Unit test dasar untuk kasus sukses dan path ilegal

### Referensi
Lihat bagian **4.1 Tool Prioritas P0** di `RUKA_Coding_Agent_Design.md`

---

## Issue #2 — [Phase 1] Implement `edit_file` Tool (Search & Replace) [COMPLETED]

**Labels:** `enhancement`, `phase-1`, `tools`, `priority:high`  
**Status:** Completed & Tested

### Deskripsi
Tool paling kritis untuk coding agent. Harus mendukung search-and-replace yang aman dan akurat.

### Acceptance Criteria
- [x] Menerima parameter: `path`, `old_string`, `new_string`, `replace_all` (default False)
- [x] Jika `old_string` tidak ditemukan → kembalikan error yang jelas
- [x] Jika ditemukan lebih dari satu dan `replace_all=False` → kembalikan error (mencegah edit yang ambigu)
- [x] Berhasil melakukan penggantian dan mengembalikan diff singkat atau konfirmasi
- [x] Mematuhi Path Jail
- [x] Unit test mencakup: sukses, tidak ditemukan, multiple match, replace_all

### Catatan Desain
Utamakan keamanan dan kejelasan error daripada kecanggihan.

---

## Issue #3 — [Phase 1] Implement `run_terminal` Tool dengan Safety Guard [COMPLETED]

**Labels:** `enhancement`, `phase-1`, `tools`, `security`, `priority:high`  
**Status:** Completed & Tested

### Deskripsi
Tool untuk mengeksekusi perintah terminal secara aman.

### Acceptance Criteria
- [x] Menerima `command`, `working_directory` (opsional), `timeout_seconds` (default 60)
- [x] Timeout dihormati (proses dibunuh jika melebihi batas)
- [x] Output (stdout + stderr) dikembalikan dengan pembatasan panjang
- [x] Daftar perintah berbahaya (rm -rf, git push --force, mkfs, dll) wajib memiliki flag konfirmasi atau ditolak
- [x] Bekerja di dalam Path Jail / working directory yang diizinkan
- [x] Unit test untuk timeout, perintah sukses, dan perintah berbahaya

---

## Issue #4 — [Phase 1] Implement Navigation & Search Tools (`list_dir`, `glob`, `grep`) [COMPLETED]

**Labels:** `enhancement`, `phase-1`, `tools`, `priority:high`  
**Status:** Completed & Tested

### Deskripsi
Tool untuk menavigasi dan mencari di dalam codebase.

### Acceptance Criteria
- [x] `list_dir` — menampilkan isi direktori (file + folder)
- [x] `glob` — pencarian file berdasarkan pola
- [x] `grep` — pencarian teks dengan dukungan regex sederhana, case insensitive, dan pembatasan hasil
- [x] Semua tool menghormati Path Jail
- [x] Hasil tidak berlebihan (ada `max_results`)

---

## Issue #5 — [Phase 1] Update Doctrine Core untuk Coding Mode [COMPLETED]

**Labels:** `enhancement`, `phase-1`, `identity`, `priority:high`  
**Status:** Completed & Tested

### Deskripsi
Perbarui Identity / Doctrine Core agar Ruka dapat menjadi coding agent yang kompeten tanpa kehilangan kepribadian.

### Acceptance Criteria
- [x] Doctrine mengandung aturan tegas: blok kode harus murni
- [x] Aturan sapaan ("Young Lord", "My Lord", "Sir") tetap dijaga
- [x] Ada instruksi khusus saat menangani tugas coding
- [x] Ada aturan wajib konfirmasi untuk aksi berbahaya
- [x] Perubahan tidak merusak test persona yang sudah ada

### Referensi
Gunakan contoh Doctrine di bagian **5** pada `RUKA_Coding_Agent_Design.md`

---

## Issue #6 — [Phase 1] Integrasi Tool Baru ke Registry & Brain [COMPLETED]

**Labels:** `enhancement`, `phase-1`, `integration`, `priority:high`  
**Status:** Completed & Tested

### Deskripsi
Mendaftarkan semua tool coding baru ke sistem dan memastikan Brain dapat menggunakannya.

### Acceptance Criteria
- [x] Semua tool P0 terdaftar di `ToolRegistry`
- [x] Brain / Orchestrator dapat memanggil tool tersebut saat intent coding terdeteksi
- [x] Tidak ada regresi pada mode Companion biasa
- [x] Logging yang cukup untuk debugging

---

## Issue #7 — [Phase 2] Implementasi CodeEvaluator Sederhana [COMPLETED]

**Labels:** `enhancement`, `phase-2`, `agentic`  
**Status:** Completed & Tested (10/10 Phase 2 Unit Tests Passing)

### Deskripsi
Setelah melakukan edit atau menjalankan perintah, sistem harus bisa mengevaluasi hasilnya secara otomatis.

### Acceptance Criteria
- [x] Setelah `edit_file` → cek syntax error dasar (bisa pakai `ast.parse` untuk Python)
- [x] Deteksi kegagalan test jika user menjalankan test
- [x] Hasil evaluasi dikembalikan ke agent loop agar bisa melakukan self-correction
- [x] Tidak terlalu lambat

---

## Issue #8 — [Phase 2] Self-Correction Loop [COMPLETED]

**Labels:** `enhancement`, `phase-2`, `agentic`  
**Status:** Completed & Tested

### Deskripsi
Jika CodeEvaluator melaporkan kegagalan, Ruka harus mencoba memperbaiki secara otomatis (dengan batas maksimum).

### Acceptance Criteria
- [x] Maksimal 3 kali percobaan perbaikan otomatis
- [x] Setiap percobaan memanfaatkan observasi dari evaluator
- [x] Tetap mematuhi LoopGuard dan Budget
- [x] Memberi tahu Young Lord jika akhirnya gagal setelah batas percobaan

---

## Issue #9 — [Phase 2] Perluasan Intent Classifier (MLP) [COMPLETED]

**Labels:** `enhancement`, `phase-2`, `neural`  
**Status:** Completed & Tested

### Deskripsi
Perluas kelas intent agar routing coding lebih akurat.

### Kelas Baru yang Disarankan
- `coding_implement`
- `coding_debug`
- `coding_refactor`
- `coding_review`
- `coding_explain`

### Acceptance Criteria
- [x] Model MLP diperbarui dan ditraining ulang (atau fallback rule-based sementara)
- [x] Akurasi tidak turun drastis pada kelas lama
- [x] Routing ke coding tools menjadi lebih tepat

---

## Issue #10 — [Phase 2] Project Memory Dasar [COMPLETED]

**Labels:** `enhancement`, `phase-2`, `memory`  
**Status:** Completed & Tested

### Deskripsi
Simpan pengetahuan khusus per project/repository.

### Acceptance Criteria
- [x] Bisa menyimpan dan mengambil memori berdasarkan path project atau git remote
- [x] Digunakan untuk menyimpan coding convention, arsitektur, dan keputusan penting
- [x] Terintegrasi dengan MemoryManager yang sudah ada

---

## Issue #11 — [Phase 3] Peningkatan Pengalaman CLI [COMPLETED]

**Labels:** `enhancement`, `phase-3`, `ux`, `cli`  
**Status:** Completed & Tested (6/6 Phase 3 Unit Tests Passing)

### Deskripsi
Membuat pengalaman CLI lebih nyaman untuk coding agent.

### Acceptance Criteria
- [x] `ruka` tanpa argumen masuk ke REPL yang nyaman
- [x] Support perintah seperti `ruka review <path>`, `ruka agent "<task>"`
- [x] Output tetap mempertahankan persona Ruka
- [x] History dan auto-complete sederhana (opsional)

---

## Issue #12 — [Phase 3] Git Tools Dasar [COMPLETED]

**Labels:** `enhancement`, `phase-3`, `tools`  
**Status:** Completed & Tested

### Deskripsi
Tambahkan kesadaran terhadap git.

### Acceptance Criteria
- [x] `git_status`
- [x] `git_diff`
- [x] `git_log` (ringkas)
- [x] Opsional: `create_commit` dengan konfirmasi dan pesan bergaya Ruka

---

## Template Tambahan (Opsional)

Gunakan template ini jika ingin menambah issue baru:

```markdown
## Issue #XX — [Phase X] Judul Singkat

**Labels:** `enhancement`, `phase-X`, ...

### Deskripsi
...

### Acceptance Criteria
- [ ] ...
- [ ] ...

### Referensi
...
```

---

**Catatan untuk Maintainer:**  
Disarankan membuat Milestone:
- `Phase 1 - Foundation`
- `Phase 2 - Agentic`
- `Phase 3 - Polish`

Dan label:
- `phase-1`, `phase-2`, `phase-3`
- `tools`, `agentic`, `identity`, `security`, `priority:high`
