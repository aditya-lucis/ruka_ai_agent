# SKILL_SPEC.md — Spesifikasi Resmi Format SKILL.md RUKA

**Versi Spesifikasi:** 1.0.0  
**Tanggal:** 2 Oktober 2026  
**Status:** Standar Resmi Marquis of Trendamis Skills System  

---

## 1. Pendahuluan

Setiap kemampuan (Skill) yang dapat dipanggil oleh Ruka didefinisikan dalam sebuah direktori mandiri yang wajib memuat satu berkas utama: `SKILL.md`.  
Format ini memadukan **YAML Frontmatter** untuk metadata terstruktur mesin dan **Markdown Body** untuk instruksi kognitif System 2 serta pedoman pemakaian manusia/agen.

---

## 2. Struktur Berkas

```
skills/<nama_skill>/
├── SKILL.md              # WAJIB: Metadata YAML & petunjuk kognitif
├── main.py               # OPSIONAL: Entry point eksekusi kode Python
├── requirements.txt      # OPSIONAL: Dependensi eksternal jika ada
└── examples/             # OPSIONAL: Contoh pemanggilan
```

---

## 3. Skema YAML Frontmatter

Frontmatter wajib diletakkan di baris paling awal berkas `SKILL.md`, diapit oleh sepasang pembatas triple-dash (`---`).

### 3.1 Field Wajib (Mandatory)

| Field         | Tipe           | Deskripsi |
|---------------|----------------|-----------|
| `name`        | `string`       | Pengidentifikasi unik skill (huruf kecil, underscore). |
| `version`     | `string`       | SemVer (contoh: `1.0.0`). |
| `description` | `string`       | Ringkasan tujuan dan skenario penggunaan skill. |
| `risk_level`  | `string`       | Tingkat risiko: `low`, `medium`, `high`, atau `critical`. |
| `permissions` | `list[string]` | Daftar izin yang dibutuhkan (contoh: `filesystem:read`, `shell:execute`). |

### 3.2 Field Opsional (Recommended)

| Field                    | Tipe           | Default | Deskripsi |
|--------------------------|----------------|---------|-----------|
| `author`                 | `string`       | `"Ruka Core Team"` | Penulis atau pengembang skill. |
| `license`                | `string`       | `"MIT"` | Lisensi distribusi. |
| `tags`                   | `list[string]` | `[]`    | Tag kategori pencarian (contoh: `[coding, search]`). |
| `requires_confirmation`  | `boolean`      | `false` | Apakah wajib meminta izin Young Lord sebelum eksekusi. |
| `entry_point`            | `string`       | `None`  | Berkas skrip utama (contoh: `main.py`). |
| `timeout_seconds`        | `float`        | `30.0`  | Batas waktu eksekusi dalam detik. |

---

## 4. Contoh Lengkap

### Contoh 1: `code_edit` (Code Skill)

```markdown
---
name: code_edit
version: 1.0.0
description: |
  Melakukan edit file secara presisi menggunakan mekanisme search-and-replace yang aman.
  Digunakan untuk perubahan kode terarah tanpa risiko rewrite penuh.
author: Ruka Core Team
license: MIT
tags: [coding, filesystem, edit]
risk_level: medium
requires_confirmation: false
permissions:
  - filesystem:read
  - filesystem:write
entry_point: main.py
timeout_seconds: 30
---

# Code Edit Skill

## Kapan Digunakan
- Saat perlu mengubah sebagian teks atau memperbaiki fungsi tertentu.
- Jangan gunakan untuk file baru (gunakan `code_write`).

## Aturan Keamanan
- Wajib melalui Path Jail.
- Jika teks lama muncul lebih dari 1 kali dan `replace_all=false`, operasi ditolak.
```

### Contoh 2: `web_search` (Utility Skill)

```markdown
---
name: web_search
version: 1.0.0
description: |
  Melakukan pencarian informasi terkini dari internet melalui Google Search Engine.
author: Ruka Core Team
license: MIT
tags: [search, web, intelligence]
risk_level: low
requires_confirmation: false
permissions:
  - network:fetch
timeout_seconds: 15
---

# Web Search Skill

## Kapan Digunakan
- Saat Young Lord menanyakan dokumentasi teknologi terbaru, berita, atau informasi luar.
```

### Contoh 3: `self_reflect` (Prompt/Cognitive Skill)

```markdown
---
name: self_reflect
version: 1.0.0
description: |
  Mengevaluasi kembali rangkaian keputusan dan hasil kerja sebelum melapor ke Young Lord.
author: Ruka Core Team
license: MIT
tags: [cognitive, reflection, quality]
risk_level: low
requires_confirmation: false
permissions: []
timeout_seconds: 20
---

# Self Reflect Skill

## Kapan Digunakan
- Setelah eksekusi plan yang rumit, untuk memastikan tidak ada asumsi yang keliru.
```

---

## 5. Penegakan Keamanan & Path Jail

1. Setiap pemanggilan skill dengan parameter jalur berkas (`path`, `target_path`, dsb.) diverifikasi oleh **Path Jail**.
2. Skill dengan `risk_level: high` atau `critical` atau dengan `requires_confirmation: true` secara otomatis memicu event konfirmasi ke Young Lord.
3. Eksekusi yang melebihi `timeout_seconds` akan dihentikan paksa oleh runtime.
