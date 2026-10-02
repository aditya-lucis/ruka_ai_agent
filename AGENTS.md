# AGENTS.md — Instruksi untuk AI Coding Agents & Kontributor

**Proyek:** Ruka AI Agent  
**Tujuan Saat Ini:** Mengembangkan kemampuan Coding Agent setara Claude Code sambil **mempertahankan 100% kepribadian dan lore** Ruka (Marquis of Trendamis).

Dokumen ini wajib dibaca oleh setiap AI Agent (Claude, Gemini, Cursor, Windsurf, dll) dan kontributor manusia sebelum melakukan perubahan kode.

---

## 1. Prinsip Mutlak (Tidak Boleh Dilanggar)

1. **Kepribadian & Lore tidak boleh dimatikan**  
   Ruka tetap harus berbicara sebagai Marquis vampir bangsawan yang tenang, berwibawa, sedikit tengil, dan sangat loyal kepada "Young Lord" / "My Lord" / "Sir".

2. **Blok kode harus murni**  
   Di dalam fenced code block (```), dilarang keras memasukkan sapaan, gaya bicara, atau narasi. Kode harus bersih dan profesional.

3. **Path Jail dan keamanan tetap dijaga**  
   Jangan pernah melemahkan sistem Path Jail atau menambahkan tool yang bisa mengakses di luar sandbox tanpa konfirmasi.

4. **Jangan merusak fitur Companion yang sudah ada**  
   Voice, vision, memory, identity engine, dan desktop UI harus tetap berfungsi.

5. **Tulis kode yang bersih, typed, dan teruji**  
   Ikuti gaya kode yang sudah ada di `ruka-agent`. Gunakan type hints, docstring, dan buat test jika memungkinkan.

---

## 2. Arsitektur Singkat yang Harus Dipahami

- **Brain** → `ruka-agent/src/ruka_cognition/brain.py` + `src/agent/`
- **Tool System** → `ruka-agent/src/tools/`
- **Identity & Doctrine** → `ruka-companion` + Identity store
- **Orchestrator & Planner** → `src/agent/orchestrator.py` + `planner.py`
- **Launcher / IPC** → `launcher.py`

Baca terlebih dahulu:
- `book/RUKA_Coding_Agent_Design.md` (dokumen rancangan utama)
- `src/agent/orchestrator.py`
- `src/tools/registry.py`
- `src/neural/intent.py`

---

## 3. Prioritas Pengembangan Saat Ini

Kerjakan sesuai urutan fase berikut (jangan loncat sembarangan):

### Fase 1 — Fondasi Tool Coding (Prioritas Tertinggi)
- [x] `read_file` + `read_files`
- [x] `edit_file` (search & replace)
- [x] `write_file`
- [x] `run_terminal` (dengan timeout + safety)
- [x] `list_dir`, `glob`, `grep`
- [x] Integrasi ke `ToolRegistry`
- [x] Update Doctrine Core agar mendukung coding mode

### Fase 2 — Agentic Capability
- [x] CodeEvaluator sederhana
- [x] Self-correction loop
- [x] Perluasan Intent Classifier (MLP)
- [x] Project Memory dasar

### Fase 3 — Pengalaman Pengguna
- [x] CLI experience yang mulus
- [x] Plan transparency
- [x] Git tools dasar

---

## 4. Aturan Penulisan Kode

- Gunakan Python 3.10+ type hints.
- Ikuti struktur folder yang sudah ada.
- Semua tool baru harus mewarisi `BaseTool` dan terdaftar di registry.
- Setiap tool berbahaya wajib memiliki mekanisme konfirmasi atau flag `require_confirmation`.
- Jangan hardcode API key atau path absolut.
- Tulis test untuk logic penting (terutama tool dan safety guard).

---

## 5. Cara Menjaga Persona Saat Mengubah Prompt / Doctrine

Saat mengedit system prompt atau Doctrine:

- Jangan menghapus aturan sapaan ("Young Lord", "My Lord", "Sir").
- Jangan menambahkan instruksi yang menyuruh Ruka menjadi "professional and concise only".
- Selalu sisipkan aturan:  
  > "Saat menghasilkan kode, blok kode harus murni. Gaya bicara aristokrat hanya di luar blok kode."

---

## 6. Testing

- Jalankan test yang sudah ada: `pytest` di folder `ruka-agent`.
- Jika menambah tool baru, buat minimal unit test untuk kasus sukses dan gagal.
- Ada test suite persona — jangan biarkan test tersebut rusak.

---

## 7. Gaya Komunikasi AI Agent (Opsional tapi Disarankan)

Ketika AI Agent (seperti kamu) memberikan penjelasan atau membuat commit message di proyek ini, diperbolehkan menggunakan sedikit gaya Ruka agar konsisten dengan proyek, contoh:

> "Young Lord, hamba telah menambahkan tool `edit_file` dengan mekanisme search-replace yang aman..."

Namun prioritas utama tetap kejelasan teknis.

---

## 8. Referensi Dokumen

- **Rancangan Utama:** `book/RUKA_Coding_Agent_Design.md`
- **Issue GitHub Ready:** `GITHUB_ISSUES.md`
- Source code utama: folder `ruka-agent/src/`

---

**Ingat:**  
Tujuan kita bukan membuat Claude Code biasa.  
Tujuan kita adalah menciptakan **Marquis yang menguasai seni pemrograman**.

Bekerja dengan presisi dan kehormatan.

— Ruka Development Guidelines
