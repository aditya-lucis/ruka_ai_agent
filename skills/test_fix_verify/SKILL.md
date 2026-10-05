---
name: test_fix_verify
version: 1.0.0
description: |
  Siklus otonom terarah untuk menjalankan unit test, menganalisis kegagalan
  secara terstruktur, menerapkan perbaikan berkas kode, dan memverifikasi ulang
  hasil pengujian hingga seluruh test lulus atau batas retry tercapai.
author: Ruka Core Team
license: MIT
tags: [coding, test, fix, verify, autonomous, loop]
risk_level: high
requires_confirmation: true
permissions:
  - shell:execute
  - filesystem:write
timeout_seconds: 120
---

# Test -> Fix -> Verify Skill

## Kapan Digunakan
- Saat Young Lord meminta memverifikasi atau memperbaiki kegagalan pengujian proyek secara otonom.
- Saat melakukan refactoring atau implementasi fitur dan ingin memastikan seluruh test suite tetap hijau (`passing`).

## Parameter
- `command`: Perintah pengujian yang akan dijalankan di dalam workspace (default: `pytest`).
- `max_retries`: Jumlah iterasi perbaikan maksimal yang diizinkan (default: `3`).

## Cara Kerja
1. **Test**: Menjalankan test runner yang ditentukan. Jika sudah lulus, siklus langsung selesai dengan status `already_passing`.
2. **Analyze**: Mengekstrak berkas target, nomor baris, tipe error, dan traceback secara deterministik.
3. **Fix**: Merumuskan hipotesis perbaikan, menguji sintaks secara aman dengan evaluator kode, lalu menerapkan edit pada berkas terkait.
4. **Verify**: Menjalankan ulang test untuk memastikan perbaikan tidak menimbulkan regresi.

## Keamanan & Pengawasan
- Beroperasi dalam batas ketat `PathJail`.
- Memerlukan tiket persetujuan (`requires_confirmation: true`) karena memodifikasi berkas dan mengeksekusi shell.
