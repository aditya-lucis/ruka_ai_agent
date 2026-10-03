---
name: git_log
version: 1.0.0
description: |
  Menampilkan riwayat commit git (hash, pengarang, tanggal, dan pesan commit) di dalam workspace.
author: Ruka Core Team
license: MIT
tags: [coding, git, inspection, log, history]
risk_level: low
requires_confirmation: false
permissions:
  - filesystem:read
timeout_seconds: 10
---

# Git Log Skill

## Kapan Digunakan
- Saat Young Lord meminta memeriksa riwayat commit (`git log`, commit terakhir, siapa yang mengubah).
- Memeriksa jejak riwayat berkas tertentu.

## Parameter
- `path`: Direktori atau berkas target untuk riwayat git (default: `.`).
- `max_count`: Jumlah maksimal entri commit yang ditampilkan (1-50, default: 10).

## Keamanan
- Berjalan di dalam batas PathJail.
- Read-only, tidak memodifikasi riwayat commit.
