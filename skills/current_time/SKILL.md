---
name: current_time
version: 1.0.0
description: |
  Membaca waktu, hari, tanggal, dan zona waktu lokal sistem saat ini secara presisi dan real-time.
author: Ruka Core Team
license: MIT
tags: [ambient, sensor, temporal, clock, time]
risk_level: low
requires_confirmation: false
permissions:
  - filesystem:read
timeout_seconds: 5
---

# Current Time Skill

## Kapan Digunakan
- Saat Young Lord menanyakan waktu, jam berapa sekarang, hari apa hari ini, tanggal berapa, atau periode waktu (pagi/siang/sore/malam).
- Memberikan kesadaran temporal nyata kepada kognisi Ruka tanpa estimasi fiktif.

## Parameter
- Tidak memerlukan parameter.

## Keamanan
- 100% lokal, membaca jam internal perangkat pengguna tanpa akses jaringan eksternal.
