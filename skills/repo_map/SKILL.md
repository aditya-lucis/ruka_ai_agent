---
name: repo_map
version: 1.0.0
description: |
  Memetakan arsitektur dan struktur repositori/proyek: deteksi teknologi (manifest),
  hierarki folder hingga kedalaman tertentu, statistik ekstensi berkas, dan status git.
author: Ruka Core Team
license: MIT
tags: [coding, project, architecture, map, inspection]
risk_level: low
requires_confirmation: false
permissions:
  - filesystem:read
timeout_seconds: 10
---

# Repo Map Skill

## Kapan Digunakan
- Saat Young Lord meminta analisis struktur proyek, ringkasan arsitektur repositori, atau orientasi awal codebase baru.
- Membantu Agentic Loop memahami konteks proyek secara holistik dan efisien token sebelum membuat perencanaan yang kompleks.

## Parameter
- `path`: Direktori target yang akan dipetakan di dalam workspace (default: `.`).
- `max_depth`: Kedalaman maksimal penjelajahan pohon direktori (1-5, default: `2`).
- `include_stats`: Boolean, sertakan statistik ekstensi berkas dan manifest (default: `true`).

## Keamanan
- Berjalan di dalam batas PathJail.
- Read-only, tidak mengubah berkas atau struktur direktori apa pun.
