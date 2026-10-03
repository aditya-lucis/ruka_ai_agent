---
name: list_dir
version: 1.0.0
description: |
  Menampilkan isi direktori (daftar file dan sub-folder) di dalam workspace.
  Read-only, tanpa eksekusi shell, sehingga aman dipakai untuk eksplorasi struktur proyek.
author: Ruka Core Team
license: MIT
tags: [coding, filesystem, read, inspection, directory]
risk_level: low
requires_confirmation: false
permissions:
  - filesystem:read
timeout_seconds: 5
---

# List Dir Skill

## Kapan Digunakan
- Saat Young Lord meminta melihat isi folder, struktur proyek, atau `ls` / `dir`.
- Sebelum membaca atau mengedit file untuk memastikan jalurnya benar.

## Parameter
- `path`: Direktori relatif atau absolut di dalam workspace (default: `.`).

## Keamanan
- Jalur dikurung oleh PathJail; akses di luar workspace ditolak.
- Tidak menjalankan perintah shell, sehingga tidak memerlukan konfirmasi.
