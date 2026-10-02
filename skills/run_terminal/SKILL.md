---
name: run_terminal
version: 1.0.0
description: |
  Menjalankan perintah terminal/shell (seperti pytest, git, build tool) secara terkontrol
  dengan batas waktu ketat dan proteksi perintah berbahaya.
author: Ruka Core Team
license: MIT
tags: [coding, terminal, shell, execution]
risk_level: high
requires_confirmation: false
permissions:
  - shell:execute
timeout_seconds: 60
---

# Run Terminal Skill

## Kapan Digunakan
- Saat perlu menjalankan test suite (pytest).
- Saat memeriksa git status / diff.
- Saat menjalankan kompilasi atau linter.

## Aturan Keamanan
- Perintah terlarang (rm -rf /, format, dsb.) ditolak oleh sandbox.
- Wajib memiliki batas waktu (timeout).
