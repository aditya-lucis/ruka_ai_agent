---
name: web_search
version: 1.0.0
description: |
  Mencari informasi, berita terbaru, dokumentasi teknis, dan referensi daring dari internet secara real-time.
author: Ruka Core Team
license: MIT
tags: [search, web, internet, documentation, news]
risk_level: low
requires_confirmation: false
permissions:
  - network:fetch
timeout_seconds: 15
---

# Web Search Skill

## Kapan Digunakan
- Saat Young Lord menanyakan berita terkini, perkembangan pustaka perangkat lunak terbaru, solusi error yang belum ada di dokumentasi lokal, atau pencarian web umum.
- Menghubungkan kognisi Ruka dengan sumber informasi internet langsung tanpa batasan tanggal latih model.

## Parameter
- `query`: Kalimat atau kata kunci pencarian.
- `max_results`: (Opsional) Jumlah maksimal hasil yang diambil (1-10, default: `5`).

## Keamanan
- Read-only network request melalui search engine scraper dengan fallback multi-tier.
