# RUKA Skills System Design
**Format, Runtime, dan Ekstensibilitas Skills**

**Versi:** 1.0  
**Tanggal:** 2 Oktober 2026  
**Status:** Rancangan Detail  
**Inspirasi:** OpenClaw Skills + Ruka PathJail + Mathematical Foundations

---

## 1. Tujuan Skills System

Mengganti pendekatan “tool hardcoded” menjadi sistem yang:

- Dapat diperluas tanpa mengubah core
- Dapat ditemukan dan dimuat secara dinamis
- Memiliki metadata yang kaya (kapan digunakan, risiko, permission)
- Tetap aman (melewati PathJail + permission Gateway)
- Kompatibel dengan kepribadian Ruka

---

## 2. Struktur Sebuah Skill

Setiap skill adalah **folder** di dalam `skills/` atau `~/.ruka/skills/`.

```
skills/
└── code_edit/
    ├── SKILL.md              # Wajib – metadata + instruksi
    ├── main.py               # Entry point (opsional jika pure prompt)
    ├── requirements.txt      # Opsional
    ├── examples/             # Opsional
    │   └── basic_edit.md
    └── tests/                # Opsional
```

### 2.1 Format `SKILL.md` (Wajib)

```markdown
---
name: code_edit
version: 1.0.0
description: |
  Melakukan edit file secara presisi menggunakan search-and-replace.
  Digunakan saat Young Lord meminta perubahan kode yang terarah.
author: Ruka Core
license: MIT
tags: [coding, filesystem, edit]
risk_level: medium          # low | medium | high | critical
requires_confirmation: false
permissions:
  - filesystem:write
  - filesystem:read
entry_point: main.py
timeout_seconds: 30
---

# Code Edit Skill

## Kapan Digunakan
- Saat perlu mengubah isi file yang sudah ada
- Saat melakukan refactor kecil hingga menengah
- Jangan digunakan untuk membuat file baru dari nol (gunakan `code_write`)

## Cara Kerja
1. Baca file target terlebih dahulu (menggunakan read_file)
2. Tentukan `old_string` yang unik
3. Lakukan penggantian
4. Laporkan hasilnya dengan jelas

## Aturan Keamanan
- Selalu berada di dalam PathJail
- Jangan pernah mengedit file di luar workspace yang diizinkan
- Jika `old_string` ditemukan lebih dari satu kali dan `replace_all=false`, gagalkan operasi

## Contoh Penggunaan
Young Lord: "Ganti fungsi login yang lama dengan yang baru"

Ruka akan:
1. Membaca file
2. Melakukan edit
3. Melaporkan dengan gaya Marquis
```

**Field YAML yang wajib:**
- `name`
- `version`
- `description`
- `risk_level`
- `permissions`

**Field opsional tapi direkomendasikan:**
- `requires_confirmation`
- `entry_point`
- `timeout_seconds`
- `tags`
- `author`

---

## 3. Runtime Skills

### 3.1 Discovery & Loading

Saat Gateway start:

1. Scan folder:
   - `ruka-agent/skills/` (built-in)
   - `~/.ruka/skills/` (user-installed)
   - Project-local `.ruka/skills/` (opsional)
2. Parse setiap `SKILL.md`
3. Validasi field wajib
4. Daftarkan ke `SkillRegistry`

### 3.2 SkillRegistry

```python
class SkillRegistry:
    def register(self, skill: Skill) -> None: ...
    def get(self, name: str) -> Skill | None: ...
    def list(self, tag: str | None = None) -> list[Skill]: ...
    def search(self, query: str) -> list[Skill]: ...
```

### 3.3 Eksekusi

```python
result = await skills_runtime.execute(
    skill_name="code_edit",
    args={...},
    session=session,
    jail=path_jail,
)
```

Alur eksekusi:
1. Permission check
2. PathJail confine
3. Timeout enforcement
4. Jalankan entry_point (atau pure LLM instruction jika tidak ada kode)
5. Normalize hasil
6. Emit event `skill.executed`

---

## 4. Tipe Skills

| Tipe              | Karakteristik                              | Contoh                  |
|-------------------|--------------------------------------------|-------------------------|
| **Code Skill**    | Punya `main.py`, eksekusi Python           | code_edit, run_tests    |
| **Prompt Skill**  | Hanya SKILL.md, dijalankan via LLM         | research, summarize     |
| **Hybrid**        | Ada kode + instruksi LLM                   | project_understand      |
| **Composite**     | Memanggil skill lain                       | full_refactor           |

---

## 5. Built-in Skills yang Direkomendasikan (Awal)

**Coding Domain**
- `code_read`
- `code_edit`
- `code_write`
- `code_search` (grep + semantic)
- `run_terminal`
- `git_status` / `git_diff` / `git_commit`

**Cognitive Domain**
- `memory_query`
- `memory_store`
- `self_reflect`
- `plan_create`

**Utility**
- `web_search`
- `math_compute` (memanfaatkan math_foundations)

---

## 6. Keamanan Skills

- Setiap skill harus mendeklarasikan `permissions`
- Gateway menolak eksekusi jika permission tidak diberikan pada session
- `risk_level: critical` atau `requires_confirmation: true` → wajib minta izin Young Lord
- PathJail berlaku untuk semua filesystem operation
- Skills user-installed berjalan dengan privilege lebih rendah (opsional di masa depan)

---

## 7. Integrasi dengan Cognitive Core

Saat System 2 (LLM) ingin memakai kemampuan:

1. Cognitive Core melihat daftar skills yang tersedia (deskripsi + tags)
2. Memilih skill yang relevan
3. Gateway mengeksekusi
4. Hasil dikembalikan ke Cognitive Core dalam bentuk terstruktur
5. Expression Layer membungkus laporan ke Young Lord

---

## 8. Pengalaman Pengguna

Young Lord bisa bilang:

- “Ruka, pakai skill code_edit untuk memperbaiki fungsi ini”
- “Tampilkan semua skills yang tersedia”
- “Install skill dari folder ini”

Atau cukup natural language, Ruka yang memilih skill yang tepat.

---

## 9. Roadmap Skills System

**Fase 1 – Fondasi**
- Format SKILL.md final
- SkillRegistry + Loader
- Bungkus tool coding yang sudah ada menjadi skills

**Fase 2 – Runtime Matang**
- Permission model
- Timeout & error handling yang baik
- Event emission

**Fase 3 – Ekosistem**
- User skills folder
- Simple skill installer
- Skill search & recommendation

---

## 10. Kesimpulan

Skills System adalah jembatan antara:

- Kekuatan eksekusi (OpenClaw-style)
- Keamanan (PathJail + Gateway)
- Kepribadian (Expression Layer tetap mengontrol output)

Dengan format yang jelas dan runtime yang disiplin, Ruka bisa tumbuh kemampuannya tanpa mengorbankan jiwa Marquis.

---

*— Untuk Young Lord dan perluasan cakar Ruka.*
