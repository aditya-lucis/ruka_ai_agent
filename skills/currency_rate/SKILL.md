---
name: currency_rate
version: 1.0.0
description: |
  Mengambil kurs nilai tukar mata uang asing real-time (USD, IDR, EUR, SGD, JPY, GBP, CNY, AUD, MYR, dll).
author: Ruka Core Team
license: MIT
tags: [ambient, sensor, currency, forex, finance, exchange-rate]
risk_level: low
requires_confirmation: false
permissions:
  - network:fetch
timeout_seconds: 10
---

# Currency Rate Skill

## Kapan Digunakan
- Saat Young Lord menanyakan kurs dollar hari ini, nilai tukar rupiah, perbandingan EUR/IDR, SGD/IDR, JPY/IDR, atau mata uang lainnya.
- Menyediakan data pasar finansial real-time yang akurat dan terverifikasi.

## Parameter
- `base`: (Opsional) Kode mata uang dasar (default: `USD`). Contoh: `USD`, `EUR`, `SGD`, `JPY`, `IDR`.

## Keamanan
- Read-only network request melalui API nilai tukar valuta asing resmi.
