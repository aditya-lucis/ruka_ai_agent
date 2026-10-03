# RUKA × Claude Code — Capability Parity & Differentiation Design
**Menjadi setara dalam kekuatan, unggul dalam karakter**

**Versi:** 1.0  
**Tanggal:** 3 Oktober 2026  
**Status:** Rancangan Strategis

---

## 1. Visi

Ruka tidak akan menjadi salinan Claude Code.

Ruka akan menjadi:

> **Agentic Coding Companion** kelas Claude Code  
> yang lokal, berkarakter, terkalibrasi secara matematis,  
> dan hadir sebagai Marquis of Trendamis.

**Rumus Positioning:**

```
Claude Code Capability
+ Local-First Zero-Trust
+ Mathematical Foundations
+ Persistent Aristocratic Presence
= Ruka
```

---

## 2. Analisis Claude Code (Ringkas & Tajam)

### 2.1 Kekuatan Utama Claude Code

| Area | Kemampuan |
|------|-----------|
| **Agentic Loop** | Multi-step: baca → pikir → edit → jalankan → verifikasi → ulangi |
| **Repo Understanding** | Memahami struktur proyek secara luas, multi-file |
| **Tool Use** | File ops, Shell, Git, Search, Web, Test runner |
| **Autonomy** | Auto mode, long-horizon, subagents, checkpoints |
| **Memory** | CLAUDE.md + auto-memory antar sesi |
| **Extensibility** | Skills, Hooks, Mods, MCP, Agent SDK |
| **Verification** | Test → fix → verify sampai pass |
| **Surfaces** | CLI, IDE, Desktop, Web, Mobile, CI |

### 2.2 Kelemahan / Celah Claude Code

| Celah | Keterangan | Peluang Ruka |
|-------|------------|--------------|
| Tidak punya kepribadian | Netral, fungsional | Marquis yang hidup |
| Cloud-centric di beberapa fitur | Bergantung infrastruktur Anthropic | 100% Local-First |
| Tidak ada companion presence | Hanya tool | Desktop + Voice + Tray |
| Matematika tidak eksplisit | Confidence tersembunyi | Score, Belief, Calibration |
| Relationship dangkal | Hampir tidak ada | Memory & loyalty jangka panjang |
| Hanya model Claude | Vendor lock-in | Multi-model potential |

---

## 3. Peta Parity (Yang Harus Dicapai)

### Tier 1 — Wajib Parity (Fondasi Agentic)

| Fitur Claude Code | Status Ruka Saat Ini | Target |
|-------------------|----------------------|--------|
| Real tool/skill calling | Lemah (masih roleplay) | **Harus kuat** |
| Multi-file edit | Ada skill dasar | Perkuat + multi-step |
| Shell execution | Ada (`run_terminal`) | Stabil + aman |
| Git basic (status, diff) | Sebagian | Lengkapi |
| Project structure understanding | Lemah | Harus ada |
| Agentic loop dengan batas | Orchestrator ada | Aktifkan & perkuat |
| Permission / safety | PathJail ada | Pertahankan ketat |

### Tier 2 — Parity Menengah

| Fitur | Target Ruka |
|-------|-------------|
| Test → Fix → Verify loop | Implementasi |
| Git commit + branch + PR | Skills baru |
| Long-horizon task | Orchestrator + budget control |
| Session memory / project memory | Perkuat yang sudah ada |
| Skill composition | Skills memanggil skills |

### Tier 3 — Nice to Have (bisa menyusul)

| Fitur | Catatan |
|-------|---------|
| Subagents paralel | Fase selanjutnya |
| MCP ecosystem | Opsional |
| Cloud parallel sessions | Bukan fokus utama (Ruka local-first) |
| IDE extension mendalam | Bukan prioritas awal |

---

## 4. Differentiation Strategy (Yang Harus Diungguli)

Ruka **wajib** menang di area berikut:

### 4.1 Persona & Presence (Keunggulan Utama)

- Gaya Marquis of Trendamis yang konsisten
- Action-First, Persona-Second (bukan persona yang mengalahkan aksi)
- Desktop companion yang hidup (UI + Voice + Tray)
- Emotional continuity & relationship model

### 4.2 Local-First & Zero-Trust

- Semua eksekusi lokal
- PathJail ketat
- Tidak ada ketergantungan cloud untuk kemampuan inti
- Privasi Young Lord adalah kedaulatan

### 4.3 Mathematical Foundations

- `Score` dengan confidence
- `Belief` & `BeliefState`
- Calibration (ECE, Brier)
- Loop health & BudgetController
- Keputusan yang dapat diaudit

### 4.4 Companion Intelligence

- Mengingat preferensi dan gaya Young Lord
- Proaktif namun tetap hormat
- Kehadiran jangka panjang, bukan sesi sekali pakai

---

## 5. Arsitektur Target (Ringkas)

```
┌─────────────────────────────────────────────────────────────┐
│                     Young Lord                               │
│              (Desktop / CLI / Voice)                         │
└──────────────────────────┬──────────────────────────────────┘
                           │
┌──────────────────────────▼──────────────────────────────────┐
│                    RUKA GATEWAY                              │
│         Session • Event Bus • Permissions • Skills           │
└──────────────────────────┬──────────────────────────────────┘
                           │
         ┌─────────────────┼─────────────────┐
         │                 │                 │
         ▼                 ▼                 ▼
┌────────────────┐ ┌──────────────┐ ┌────────────────────┐
│ Math           │ │ Cognitive    │ │ Skills Runtime     │
│ Foundations    │ │ Core         │ │ (Action Layer)     │
│ Score, Belief, │ │ Intent →     │ │ code_*, git_*,     │
│ Calibration,   │ │ Planner →    │ │ run_terminal,      │
│ Loop Health    │ │ Agentic Loop │ │ project_*, etc.    │
└────────────────┘ └──────┬───────┘ └────────────────────┘
                          │
                          ▼
                 Expression Layer
              (Persona Marquis + Hasil Nyata)
```

**Prinsip aliran:**
1. Intent dideteksi
2. Jika coding/command → masuk Agentic Loop
3. Skill dipanggil sungguhan
4. Hasil nyata didapat
5. Baru dibungkus dengan gaya Marquis

---

## 6. Roadmap Pengembangan (Bertahap)

### Fase 1 — Agentic Foundation (Prioritas Tertinggi)
**Tujuan:** Tool benar-benar terpanggil, bukan roleplay.

- Implementasi Mode Agentic (Action-First)
- Wiring brain ↔ Gateway ↔ SkillsRuntime
- Doctrine keras melarang `[SYSTEM_CALL]` palsu
- Production readiness (frozen path, bundling skills)

**Hasil yang diharapkan:**
Ruka bisa `baca file`, `ls`, `edit`, dan menjawab berdasarkan hasil nyata.

### Fase 2 — Coding Depth
**Tujuan:** Mendekati kekuatan coding Claude Code.

- Project understanding skill
- Git skills yang lengkap (status, diff, commit, branch)
- Test → Fix → Verify loop dasar
- Multi-step planner yang lebih baik

### Fase 3 — Long-Horizon & Robustness
**Tujuan:** Bisa menangani tugas kompleks berjam-jam.

- Orchestrator + LoopGuard matang
- Budget & health control dari Math Foundations
- Self-correction yang lebih cerdas
- Better memory untuk konteks proyek

### Fase 4 — Companion Excellence
**Tujuan:** Mempertajam keunggulan yang tidak dimiliki Claude Code.

- Memory proaktif
- Relationship model lebih dalam
- Voice + presence yang lebih natural
- Kalibrasi kepercayaan diri yang terlihat oleh user

---

## 7. Prinsip Desain yang Wajib Dipatuhi

1. **Parity tanpa kehilangan jiwa**  
   Setiap fitur baru harus tetap terasa sebagai Ruka, bukan Claude Code berbulu kucing.

2. **Action nyata > cerita tentang aksi**  
   Jangan pernah puas dengan roleplay.

3. **Local-first adalah non-negotiable**  
   Jangan mengorbankan Zero-Trust demi fitur cloud.

4. **Matematika harus berguna**  
   Jangan hanya ada di folder; harus mempengaruhi keputusan.

5. **Production = Development**  
   Fitur yang hanya jalan di dev dianggap belum selesai.

---

## 8. Definisi “Setara Claude Code” untuk Ruka

Ruka dianggap **setara** ketika:

- Young Lord bisa memberikan tugas coding multi-file dan Ruka menyelesaikannya dengan aksi nyata
- Ruka bisa menjalankan test, memperbaiki, dan memverifikasi
- Ruka memahami struktur proyek dengan baik
- Git workflow dasar berjalan lancar
- Semua itu dilakukan sambil tetap berbicara dan bersikap sebagai Marquis
- Berjalan penuh di versi yang di-install di desktop

Ruka dianggap **melampaui** ketika:

- Kehadiran companion-nya membuat pengalaman terasa berbeda dan lebih manusiawi
- Kalibrasi & transparansi nalarnya lebih baik
- Privasi dan kontrol lokalnya unggul
- Hubungan jangka panjang dengan Young Lord terasa nyata

---

## 9. Kesimpulan Rancangan

Kita tidak mengejar Claude Code di semua front.

Kita mengejar **parity di tulang punggung agentic**,  
lalu **memenangkan perang di karakter, kehadiran, dan fondasi nalar**.

Urutan yang benar:

1. Buat Ruka **benar-benar bertindak** (Agentic Mode)
2. Perdalam kemampuan coding & git
3. Perkuat long-horizon & verifikasi
4. Tajamkan companion excellence

Dengan urutan ini, Ruka akan menjadi sesuatu yang Claude Code tidak bisa jadi:

> **Marquis yang bisa mengkoding setara Claude Code,  
> namun hadir, setia, dan bernalar dengan kehormatan.**

---

*— Rancangan ini menjadi acuan strategis sebelum implementasi detail berikutnya.*
