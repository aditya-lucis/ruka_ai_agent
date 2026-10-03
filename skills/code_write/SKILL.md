---
name: code_write
version: 1.0.0
description: |
  Menulis atau membuat file teks/kode baru secara utuh di dalam workspace.
  Membuat direktori induk secara otomatis jika belum ada.
author: Ruka Core Team
license: MIT
tags: [coding, filesystem, write, scaffold]
risk_level: medium
requires_confirmation: true
permissions:
  - filesystem:write
timeout_seconds: 30
---

# Code Write Skill

## Kapan Digunakan
- Saat membuat file kode, skrip, atau konfigurasi baru dari awal.
- Saat membuat scaffold modul baru.

## Aturan Keamanan
- Penulisan berkas terkunci dalam Path Jail.
- Jika file sudah ada dan overwrite=False, operasi ditolak demi menjaga keutuhan file.
