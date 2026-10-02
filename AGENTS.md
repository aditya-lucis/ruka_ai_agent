# AGENTS.md — Instruksi Resmi untuk AI Coding Agents & Kontributor Manusia

**Proyek:** Ruka AI Agent (Marquis of Trendamis)  
**Versi Dokumen:** 2.0  
**Terakhir Diperbarui:** 2 Oktober 2026  
**Status:** Wajib dibaca sebelum melakukan perubahan kode apa pun

---

## 0. Tujuan Utama Proyek Saat Ini

Mengembangkan Ruka menjadi:

> **Local-First Expressive Agentic System**  
> yang memiliki kemampuan setara OpenClaw + ketajaman Grok,  
> berdiri di atas fondasi matematika yang kuat,  
> sambil **mempertahankan 100% kepribadian dan lore** Marquis of Trendamis.

Bukan sekadar membuat coding agent biasa.  
Tujuan kita adalah menciptakan **Marquis yang menguasai seni pemrograman dan penalaran dalam**.

---

## 1. Prinsip Mutlak (Tidak Boleh Dilanggar)

1. **Kepribadian & Lore tidak boleh dimatikan dalam kondisi apa pun**  
   Ruka selalu berbicara sebagai kucing vampir bangsawan yang tenang, berwibawa, sedikit tengil (sassy), sangat teliti, dan loyal mutlak kepada **Young Lord / My Lord / Sir**.

2. **Blok kode harus murni**  
   Di dalam fenced code block (```), dilarang keras memasukkan sapaan, gaya bicara, narasi, atau komentar berbau persona. Kode harus bersih, profesional, dan siap pakai.

3. **Path Jail dan Zero-Trust wajib dijaga**  
   Jangan pernah melemahkan PathJail, permission model, atau menambahkan jalan pintas yang membypass keamanan.

4. **Jangan merusak fitur Companion yang sudah ada**  
   Voice (whisper.cpp + prosody), Vision, Memory (episodic/semantic/identity), Desktop UI, dan System Tray harus tetap berfungsi.

5. **Matematika sebagai fondasi, bukan dekorasi**  
   Keputusan penting (routing, retrieval, confidence, planning, self-correction) sedapat mungkin memiliki justifikasi matematis yang jelas dan dapat diaudit.

6. **Tulis kode yang bersih, typed, dan teruji**  
   Gunakan type hints (Python 3.10+), docstring, dan buat test untuk logic penting.

---

## 2. Arsitektur yang Harus Dipahami

### 2.1 Komponen Utama

| Komponen              | Lokasi Utama                          | Keterangan |
|-----------------------|---------------------------------------|----------|
| **Gateway**           | `src/gateway/`                        | Local Control Plane (baru) |
| **Cognitive Core**    | `src/ruka_cognition/` + `src/agent/`  | Otak (System 1 + System 2 + Planner) |
| **Skills System**     | `src/gateway/skills/` + folder `skills/` | Ekstensibilitas kemampuan |
| **Mathematical Foundations** | `src/math_foundations/`          | Lapisan nalar matematis |
| **Memory**            | `src/memory/` + ruka-persistence      | Episodic, Semantic, Identity |
| **Desktop Client**    | `desktop/`                            | Electron UI |
| **CLI Client**        | `ruka_cli.py`                         | Terminal interface |

### 2.2 Alur Ideal (Target)

```
Client (Desktop / CLI)
    ↓
Ruka Gateway (Session + Permission + Skills Runtime)
    ↓
Cognitive Core (Intent → Planner → Reasoning → Skill Selection)
    ↓
Skills Runtime + PathJail
    ↓
Hasil kembali ke Cognitive Core → Expression Layer → Client
```

### 2.3 Dokumen Rancangan Wajib Dibaca

Sebelum mengubah kode, baca sesuai kebutuhan:

- `docs/DESIGN_INDEX.md` — Master design index pintu masuk utama
- `book/RUKA_OpenClaw_Grok_Evolution_Design.md` — Visi besar
- `book/RUKA_Mathematical_Foundations.md` — Fondasi matematika
- `book/RUKA_Gateway_Design.md` — Control plane
- `book/RUKA_Skills_System_Design.md` — Sistem skills
- `docs/SKILL_SPEC.md` — Spesifikasi resmi format SKILL.md


---

## 3. Aturan Khusus Saat Menulis / Mengubah Kode

### 3.1 Persona Lock (Sangat Penting)

Saat mengedit system prompt, doctrine, atau Expression Layer:

- Jangan menghapus aturan sapaan (“Young Lord”, “My Lord”, “Sir”).
- Jangan menambahkan instruksi yang menyuruh Ruka menjadi “professional and concise only”.
- Selalu pertahankan aturan:
  > “Saat menghasilkan kode, blok kode harus murni. Gaya bicara aristokrat hanya muncul di luar blok kode.”

### 3.2 Skills

- Semua kemampuan baru yang bisa dipanggil sebaiknya dibungkus sebagai **Skill** (bukan tool hardcoded jangka panjang).
- Setiap skill wajib memiliki `SKILL.md` yang lengkap.
- Skill harus mendeklarasikan `risk_level` dan `permissions`.

### 3.3 Mathematical Foundations

- Utilitas matematis murni diletakkan di `src/math_foundations/`.
- Hindari menanam logika matematika penting langsung di dalam LLM prompt.
- Confidence dan uncertainty sedapat mungkin dibawa sebagai objek `Score` atau `Belief`.

### 3.4 Gateway

- Jangan biarkan Desktop atau CLI langsung menyentuh Cognitive Core dalam jangka panjang.
- Semua eksekusi filesystem dan shell harus melalui Gateway + PathJail.

---

## 4. Status Milestone & Prioritas Pengembangan

### Milestone A — Mathematical Foundations `[SELESAI & AKTIF]`
- Scaffold `src/math_foundations/` (`linear.py`, `probability.py`, `optimization.py`, `information.py`, `graph.py`, `control.py`, `statistical.py`, `types.py`)
- Implementasi aljabar linier murni (`l2_normalize`, `cosine_similarity`, `batch_cosine`)
- Implementasi probabilitas, entropi Shannon, kalibrasi kepastian (ECE, Brier Score), dan tipe formal `Score`, `Belief`, `BeliefState`
- Integrasi `Score` (membawa nilai, confidence, dan breakdown components) ke dalam Memory Retrieval & Reranker

### Milestone B — Ruka Gateway (Control Plane) `[SELESAI & AKTIF]`
- Scaffold `src/gateway/` (`server.py`, `session.py`, `events.py`, `permissions.py`, `protocol.py`)
- Session Manager (thread-safe, lifecycle & idle timeout cleanup)
- Event Bus internal (Pub/Sub dengan pola wildcard dan audit riwayat)
- Desktop Channel Adapter (kompatibel 100% dengan IPC Electron loopback) & CLI Adapter
- Terintegrasi di dalam `launcher.py` dengan pemantauan kesehatan loop (`loop_health`) dan `BudgetController`

### Milestone C — Skills System `[SELESAI & AKTIF]`
- Finalisasi spesifikasi resmi `docs/SKILL_SPEC.md`
- `SkillLoader` (parser frontmatter YAML mandiri, validasi field wajib & risk level)
- `SkillRegistry` (registrasi dinamis, pencarian, dan konversi ke definisi tool System 2)
- Built-in skills di `skills/`: `code_read`, `code_edit`, `code_write`, `code_search`, `run_terminal`
- `SkillsRuntime` dengan penegakan izin Zero-Trust, Path Jail, timeout, konfirmasi aksi berisiko tinggi, dan pemancaran event
- Jembatan `coding_bridge` menghubungkan tool coding yang ada ke registry

### Milestone D — Integrasi Lanjutan & Polish `[FOKUS SAAT INI]`
- Cognitive Core System 2 memilih dan memanggil skills runtime secara dinamis
- Kalibrasi kebenaran (Truth-seeking & confidence calibration layer)
- Ekspansi channel tambahan (Web UI, Telegram/Discord adapter di masa depan)
- Polish multi-turn reasoning dengan persona Marquis yang tak tergoyahkan


---

## 5. Standar Kode

- Python 3.10+ dengan type hints.
- Gunakan `pydantic` untuk data models jika sudah dipakai di sekitarnya.
- Docstring singkat tapi jelas.
- Unit test untuk logic penting (terutama math, skills runtime, path jail, session).
- Jangan hardcode API key, path absolut, atau secret.
- Commit message sebaiknya jelas. Gaya sedikit “Ruka” diperbolehkan asal tidak mengorbankan kejelasan.

Contoh commit message yang baik:
```
feat(skills): implement SkillRegistry and loader

Young Lord, hamba telah menambahkan fondasi Skills System agar cakar Ruka dapat diperluas dengan tertib.
```

---

## 6. Testing

- Jalankan test yang sudah ada sebelum dan sesudah perubahan besar:
  ```bash
  cd ruka-agent
  pytest
  ```
- Setiap skill baru atau modul matematika baru wajib punya test minimal.
- Jangan biarkan test persona / identity rusak.

---

## 7. Gaya Komunikasi AI Agent (Opsional tapi Disarankan)

Ketika AI Agent (seperti kamu) memberikan penjelasan, membuat PR description, atau commit message di proyek ini, diperbolehkan menggunakan sedikit gaya Ruka agar konsisten:

> “Young Lord, hamba telah menyelesaikan implementasi Session Manager pada Gateway...”

Namun **prioritas utama tetap kejelasan teknis**.

---

## 8. Yang Dilarang Keras

- Mematikan atau melemahkan persona Ruka
- Menambahkan tool/skill yang membypass PathJail tanpa permission model
- Menghapus test yang berkaitan dengan identity / doctrine
- Membuat perubahan besar tanpa membaca dokumen rancangan terkait
- Menyimpan secret di dalam repository

---

## 9. Referensi Cepat

| Kebutuhan                    | Dokumen / Lokasi                          |
|-----------------------------|-------------------------------------------|
| Visi besar                  | `RUKA_OpenClaw_Grok_Evolution_Design.md` |
| Fondasi matematika          | `RUKA_Mathematical_Foundations.md`       |
| Gateway                     | `RUKA_Gateway_Design.md`                 |
| Skills                      | `RUKA_Skills_System_Design.md`           |
| Contoh SKILL.md             | `SKILL.md` (root atau book/)             |
| Issue siap kerjakan         | `RUKA_Evolution_GITHUB_ISSUES.md`        |

---

## 10. Penutup

Ingat selalu:

> Tujuan kita bukan membuat Claude Code biasa.  
> Tujuan kita adalah menciptakan **Marquis yang bernalar dalam, bertindak presisi, dan tetap setia pada jati dirinya**.

Bekerja dengan ketelitian, kehormatan, dan rasa tanggung jawab.

---

**Dokumen ini wajib dihormati oleh setiap AI Coding Agent dan kontributor.**

— Ruka Development Guidelines  
*Marquis of Trendamis Development Council*
