---
name: geolocation
version: 1.0.0
description: |
  Mendeteksi lokasi geografis dan koordinat GPS (latitude, longitude, kota, wilayah, negara, ISP) secara real-time.
author: Ruka Core Team
license: MIT
tags: [ambient, sensor, gps, geolocation, location]
risk_level: low
requires_confirmation: false
permissions:
  - network:fetch
timeout_seconds: 10
---

# Geolocation Skill

## Kapan Digunakan
- Saat Young Lord menanyakan lokasi saat ini, posisi GPS, koordinat perangkat, atau di kota mana ia berada.
- Memberikan kesadaran spasial nyata kepada Ruka untuk menyesuaikan konteks lokal, cuaca, dan zona waktu.

## Parameter
- Tidak memerlukan parameter.

## Keamanan
- Read-only via HTTPS query geolokasi IP. Tidak membagikan data identitas pribadi atau data lokal ke pihak ketiga.
