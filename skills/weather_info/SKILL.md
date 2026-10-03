---
name: weather_info
version: 1.0.0
description: |
  Mengambil informasi kondisi cuaca, suhu (°C), kelembapan, kecepatan angin, dan jarak pandang secara real-time.
author: Ruka Core Team
license: MIT
tags: [ambient, sensor, weather, temperature, forecast]
risk_level: low
requires_confirmation: false
permissions:
  - network:fetch
timeout_seconds: 10
---

# Weather Info Skill

## Kapan Digunakan
- Saat Young Lord menanyakan kondisi cuaca hari ini, suhu udara, apakah akan hujan, atau situasi meteorologi di kota tertentu.
- Memperkuat empati dan kesadaran lingkungan pendamping (misalnya menyarankan istirahat jika cuaca dingin/hujan).

## Parameter
- `location`: (Opsional) Nama kota atau koordinat target. Jika dikosongkan, menggunakan lokasi terdeteksi saat ini.

## Keamanan
- Read-only network request melalui penyedia data cuaca terpercaya.
