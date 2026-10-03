---
name: code_edit
version: 1.0.0
description: |
  Melakukan edit file teks/kode secara presisi menggunakan mekanisme search-and-replace yang aman.
  Digunakan untuk refactor terarah, penyesuaian fungsi, dan perbaikan bug tanpa rewrite penuh.
author: Ruka Core Team
license: MIT
tags: [coding, filesystem, edit, refactor]
risk_level: medium
requires_confirmation: true
permissions:
  - filesystem:read
  - filesystem:write
timeout_seconds: 30
---

# Code Edit Skill

## Kapan Digunakan
- Saat perlu mengubah sebagian isi file teks atau baris kode tertentu.
- Saat melakukan perbaikan bug lokal atau refactor fungsi kecil-menengah.
- Hindari untuk pembuatan file baru (gunakan `code_write`).

## Aturan Keamanan
- Selalu dibatasi dalam batas Path Jail.
- Jika old_string muncul lebih dari sekali dan replace_all bernilai False, operasi ditolak.
