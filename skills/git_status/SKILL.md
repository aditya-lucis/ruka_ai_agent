---
name: git_status
version: 1.0.0
description: |
  Memeriksa status git working tree di dalam workspace.
  Menampilkan branch saat ini, berkas yang diubah (unstaged), sudah ditambahkan (staged),
  dan berkas baru yang belum terlacak (untracked).
author: Ruka Core Team
license: MIT
tags: [coding, git, inspection, status]
risk_level: low
requires_confirmation: false
permissions:
  - filesystem:read
timeout_seconds: 10
---

# Git Status Skill

## Kapan Digunakan
- Saat Young Lord meminta memeriksa status repositori git (`git status`, perubahan apa saja yang ada).
- Sebelum melakukan commit atau setelah mengedit berkas untuk memverifikasi perubahan kerja.

## Parameter
- `path`: Direktori target git status di dalam workspace (default: `.`).

## Keamanan
- Berjalan di dalam batas PathJail.
- Read-only, tidak mengubah riwayat atau working tree git.
