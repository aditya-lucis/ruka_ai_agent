---
name: code_read
version: 1.0.0
description: |
  Membaca konten file teks atau kode sumber dengan dukungan pagination (line range / offset).
  Digunakan untuk menelaah file sebelum melakukan manipulasi kode.
author: Ruka Core Team
license: MIT
tags: [coding, filesystem, read, inspection]
risk_level: low
requires_confirmation: false
permissions:
  - filesystem:read
timeout_seconds: 15
---

# Code Read Skill

## Kapan Digunakan
- Saat perlu memeriksa atau menelaah file sumber yang sudah ada.
- Saat menyelidiki bug atau struktur konfigurasi.

## Parameter
- `path`: Jalur file relatif atau absolut dalam workspace.
- `start_line`: Baris awal pembacaan (1-indexed).
- `end_line`: Baris akhir pembacaan.
