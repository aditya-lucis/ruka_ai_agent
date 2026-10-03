---
name: git_commit
version: 1.0.0
description: |
  Melakukan commit perubahan pada git repository di dalam workspace.
  Dapat melakukan staging otomatis untuk berkas yang ditentukan atau semua berkas yang dilacak (all=true).
author: Ruka Core Team
license: MIT
tags: [coding, git, mutation, commit]
risk_level: high
requires_confirmation: true
permissions:
  - filesystem:write
  - shell:execute
timeout_seconds: 15
---

# Git Commit Skill

## Kapan Digunakan
- Saat Young Lord menginstruksikan untuk menyimpan perubahan ke repositori git dengan pesan commit tertentu.

## Parameter
- `message`: Pesan commit (wajib diisi, tidak boleh kosong).
- `files`: Daftar berkas yang ingin di-stage sebelum commit (opsional).
- `all`: Boolean, `true` jika ingin otomatis men-stage semua perubahan terlacak (`git commit -a`) (default: `false`).
- `path`: Direktori target repository di dalam workspace (default: `.`).

## Keamanan & Konfirmasi
- Berjalan di dalam batas PathJail.
- Tindakan ini mengubah riwayat git permanen.
- Mengharuskan konfirmasi tiket (`requires_confirmation: true`) sebelum eksekusi dijalankan.
