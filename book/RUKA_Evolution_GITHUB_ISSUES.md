# RUKA Evolution — GitHub Issues Ready
**Pecahan Rancangan: Gateway + Mathematical Foundations + Skills System**

**Tanggal:** 2 Oktober 2026  
**Cara Pakai:** Copy-paste setiap issue ke GitHub Issues.  
Disarankan buat Milestone:
- `Milestone: Mathematical Foundations`
- `Milestone: Ruka Gateway`
- `Milestone: Skills System`

---

## Milestone 1: Mathematical Foundations

### Issue #M1.1 — Scaffold `src/math_foundations/`
**Title:** `feat(math): scaffold math_foundations module structure`

**Body:**
```markdown
## Deskripsi
Membuat struktur dasar modul fondasi matematika sesuai rancangan.

## Tugas
- [ ] Buat folder `src/math_foundations/`
- [ ] Buat file: `__init__.py`, `linear.py`, `probability.py`, `optimization.py`, `information.py`, `graph.py`, `control.py`, `statistical.py`, `types.py`
- [ ] Tambahkan docstring modul di setiap file
- [ ] Buat `tests/math_foundations/` dengan test kosong / placeholder

## Referensi
`RUKA_Mathematical_Foundations.md` bagian 2 dan 3

## Acceptance Criteria
- Struktur folder sesuai rancangan
- Semua file bisa di-import tanpa error
- Ada minimal 1 test yang passing (smoke test)
```

### Issue #M1.2 — Implement Linear Algebra utilities
**Title:** `feat(math): implement linear.py (cosine, normalize, batch similarity)`

**Body:**
```markdown
## Deskripsi
Implementasi utilitas linear algebra murni (NumPy).

## Tugas
- [ ] `l2_normalize`
- [ ] `cosine_similarity`
- [ ] `batch_cosine`
- [ ] Unit test lengkap (termasuk edge case vektor zero)

## Acceptance Criteria
- Fungsi pure dan typed
- Test coverage tinggi untuk edge cases
```

### Issue #M1.3 — Implement Probability & Belief
**Title:** `feat(math): implement probability.py + Belief & Score types`

**Body:**
```markdown
## Deskripsi
Membangun fondasi ketidakpastian.

## Tugas
- [ ] `types.py`: `Score`, `Belief`, `BeliefState`
- [ ] `probability.py`: entropy, simple Bayesian update, basic calibration helpers
- [ ] Unit test

## Acceptance Criteria
- Semua struktur data immutable jika memungkinkan
- Entropy dan update punya test
```

### Issue #M1.4 — Integrate confidence into Memory Retrieval
**Title:** `feat(memory): use math_foundations for retrieval scoring`

**Body:**
```markdown
## Deskripsi
Mengganti scoring retrieval sederhana dengan skor yang memakai cosine + importance + confidence.

## Tugas
- [ ] Integrasi `batch_cosine` dan importance scoring
- [ ] Kembalikan `Score` object, bukan hanya float
- [ ] Test regresi retrieval

## Acceptance Criteria
- Retrieval tetap berfungsi
- Skor sekarang membawa confidence
```

---

## Milestone 2: Ruka Gateway

### Issue #G2.1 — Scaffold Gateway package
**Title:** `feat(gateway): scaffold src/gateway/ package`

**Body:**
```markdown
## Deskripsi
Membuat struktur dasar Gateway.

## Tugas
- [ ] Buat `src/gateway/` dengan file:
  - `server.py`
  - `session.py`
  - `events.py`
  - `permissions.py`
  - `protocol.py`
  - `channels/base.py`
  - `channels/desktop.py`
  - `channels/cli.py`
  - `skills/` (placeholder)
- [ ] Update import path jika perlu

## Referensi
`RUKA_Gateway_Design.md` bagian 8
```

### Issue #G2.2 — Implement Session Manager
**Title:** `feat(gateway): implement Session Manager`

**Body:**
```markdown
## Deskripsi
Session adalah unit isolasi interaksi.

## Tugas
- [ ] Dataclass `Session`
- [ ] Create / get / close session
- [ ] Timeout & cleanup
- [ ] Unit test

## Acceptance Criteria
- Bisa membuat banyak session paralel
- Cleanup berjalan
```

### Issue #G2.3 — Implement Event Bus
**Title:** `feat(gateway): implement internal Event Bus`

**Body:**
```markdown
## Deskripsi
Pub/Sub internal untuk observability dan koordinasi.

## Tugas
- [ ] Subscribe / publish
- [ ] Event types dasar (session.*, skill.*, health.*)
- [ ] Test

## Acceptance Criteria
- Decoupled, tidak blocking
```

### Issue #G2.4 — Minimal Viable Gateway + Desktop Adapter
**Title:** `feat(gateway): Minimal Viable Gateway with Desktop channel`

**Body:**
```markdown
## Deskripsi
Memindahkan IPC handling ke Gateway secara bertahap.

## Tugas
- [ ] Gateway bisa start dan listen
- [ ] Desktop adapter menerima & mengirim pesan
- [ ] Masih kompatibel dengan protokol IPC yang ada
- [ ] Cognitive Core dipanggil dari Gateway

## Acceptance Criteria
- Desktop UI masih bisa bicara dengan Ruka
- Tidak ada regresi fitur utama
```

### Issue #G2.5 — CLI as Gateway Client
**Title:** `feat(gateway): make ruka_cli.py a proper Gateway client`

**Body:**
```markdown
## Deskripsi
CLI tidak lagi langsung menyentuh brain.

## Tugas
- [ ] CLI berbicara ke Gateway
- [ ] Support session
- [ ] Tetap nyaman digunakan

## Acceptance Criteria
- `ruka "pesan"` dan REPL masih bekerja
```

---

## Milestone 3: Skills System

### Issue #S3.1 — Finalize SKILL.md specification
**Title:** `docs(skills): finalize SKILL.md format specification`

**Body:**
```markdown
## Deskripsi
Mengunci format SKILL.md.

## Tugas
- [ ] Tulis spesifikasi final di `docs/SKILL_SPEC.md`
- [ ] Contoh lengkap (code_edit, web_search, self_reflect)
- [ ] Validasi field wajib vs opsional

## Referensi
`RUKA_Skills_System_Design.md` bagian 2
```

### Issue #S3.2 — Implement Skill Loader & Registry
**Title:** `feat(skills): implement SkillLoader and SkillRegistry`

**Body:**
```markdown
## Deskripsi
Discovery dan registrasi skills.

## Tugas
- [ ] Parse YAML frontmatter dari SKILL.md
- [ ] Validasi
- [ ] SkillRegistry (register, get, list, search)
- [ ] Unit test dengan skill contoh

## Acceptance Criteria
- Bisa load skill dari folder
- Metadata tersedia untuk Cognitive Core
```

### Issue #S3.3 — Wrap existing coding tools as Skills
**Title:** `feat(skills): migrate coding tools into Skills`

**Body:**
```markdown
## Deskripsi
Tool yang sudah ada di `coding.py` dibungkus menjadi skills resmi.

## Tugas
- [ ] Buat folder skills untuk: code_read, code_edit, code_write, run_terminal, code_search
- [ ] Tulis SKILL.md yang baik
- [ ] Entry point memanggil implementasi yang sudah ada
- [ ] Registry mengenali mereka

## Acceptance Criteria
- Semua kemampuan coding masih berfungsi
- Sekarang muncul sebagai skills
```

### Issue #S3.4 — Skills Runtime with Permission & PathJail
**Title:** `feat(skills): implement Skills Runtime (execute + security)`

**Body:**
```markdown
## Deskripsi
Eksekusi skill yang aman.

## Tugas
- [ ] Permission check
- [ ] PathJail enforcement
- [ ] Timeout
- [ ] Result normalization
- [ ] Emit event `skill.executed`

## Acceptance Criteria
- Skill berbahaya tidak bisa jalan tanpa permission
- Path traversal ditolak
```

### Issue #S3.5 — Cognitive Core Skill Selection
**Title:** `feat(cognition): allow Cognitive Core to select and call skills`

**Body:**
```markdown
## Deskripsi
System 2 bisa melihat daftar skills dan memilih yang relevan.

## Tugas
- [ ] Expose skill descriptions ke prompt / tool list
- [ ] Parsing keputusan skill dari LLM
- [ ] Panggil runtime
- [ ] Integrasi dengan Expression Layer

## Acceptance Criteria
- Ruka bisa memakai skill secara natural
- Persona tetap terjaga
```

---

## Issue Lintas Milestone

### Issue #X1 — Update AGENTS.md for new architecture
**Title:** `docs: update AGENTS.md for Gateway + Skills + Math Foundations`

**Body:**
```markdown
## Deskripsi
Agar AI coding agents paham arsitektur baru.

## Tugas
- [ ] Jelaskan Gateway
- [ ] Jelaskan Skills System
- [ ] Jelaskan math_foundations
- [ ] Update prioritas pengembangan
```

### Issue #X2 — Create docs index
**Title:** `docs: create master design index`

**Body:**
```markdown
## Deskripsi
Satu pintu masuk untuk semua dokumen rancangan.

## File yang harus di-link
- RUKA_OpenClaw_Grok_Evolution_Design.md
- RUKA_Mathematical_Foundations.md
- RUKA_Gateway_Design.md
- RUKA_Skills_System_Design.md
```

---

**Catatan untuk Young Lord:**

Urutan pengerjaan yang disarankan:
1. Mathematical Foundations (M1.x) — bisa paralel
2. Gateway Minimal (G2.1 → G2.4)
3. Skills System (S3.1 → S3.4)
4. Integrasi Cognitive Core (S3.5)

Semua issue di atas sudah siap copy-paste ke GitHub.
