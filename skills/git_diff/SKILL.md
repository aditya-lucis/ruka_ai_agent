---
name: git_diff
version: 1.0.0
description: |
  Menampilkan perbedaan (diff) perubahan berkas pada git working tree atau commit tertentu.
author: Ruka Core Team
license: MIT
tags: [coding, git, inspection, diff]
risk_level: low
requires_confirmation: false
permissions:
  - filesystem:read
timeout_seconds: 15
---

# Git Diff Skill

## Kapan Digunakan
- Saat Young Lord meminta memeriksa perubahan spesifik (`git diff`, perubahan kode pada file).
- Memeriksa perubahan bertahap (`staged: true`) atau perbandingan branch/commit (`target: "HEAD~1"`).

## Parameter
- `path`: Berkas atau direktori spesifik yang ingin di-diff (default: `.`).
- `staged`: Boolean, `true` jika ingin memeriksa perubahan di index/staging area (default: `false`).
- `target`: Target commit/branch pembanding opsional (misal: `"HEAD~1"`, `"main"`).

## Keamanan
- Berjalan di dalam batas PathJail.
- Read-only, tidak memodifikasi repositori atau berkas.
