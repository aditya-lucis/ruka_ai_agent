# RUKA Evolution Design
**Menuju Local-First Agentic Companion setara OpenClaw + Grok, dengan Fondasi Matematika Kuat**

**Versi:** 2.0  
**Tanggal:** 2 Oktober 2026  
**Status:** Rancangan Strategis  
**Prinsip Inti:** Kepribadian tetap utuh • Matematika sebagai tulang punggung • Local-first • Truth-seeking

---

## 1. Visi Baru

Ruka bukan lagi sekadar Desktop Companion.

**Visi:**  
Menjadi **Local-First Expressive Agentic System** yang:

- Memiliki kehadiran dan kepribadian sekuat J.A.R.V.I.S. versi bangsawan vampir
- Memiliki kemampuan eksekusi dan skills sekuat OpenClaw
- Memiliki kedalaman reasoning dan truth-seeking sekuat Grok
- Dibangun di atas fondasi matematika yang eksplisit dan kuat (bukan hanya “pakai model”)

Tagline baru yang diusulkan:  
> *“The Marquis who reasons deeply, acts precisely, and never forgets who he serves.”*

---

## 2. Prinsip Desain Utama

1. **Kepribadian & Lore tidak boleh dikorbankan**  
   Segala kemampuan baru harus dibungkus dalam identitas Marquis of Trendamis.

2. **Matematika sebagai fondasi, bukan dekorasi**  
   Setiap komponen penting (memory, planning, confidence, routing, control) harus punya justifikasi matematis yang jelas.

3. **Local-First & Zero-Trust**  
   Data, memory, skills, dan eksekusi sedapat mungkin tetap di mesin Young Lord.

4. **Skills > Hardcoded Tools**  
   Mengadopsi filosofi OpenClaw: kemampuan diperluas melalui Skills (SKILL.md + kode), bukan hanya tool tetap.

5. **Truth-Seeking & Calibration**  
   Ruka harus mampu menyatakan ketidakpastian, menolak omong kosong, dan mengoreksi dirinya (pengaruh Grok).

6. **Dual / Multi-System Reasoning**  
   Pertahankan dan perkuat System 1 (cepat, matematis) + System 2 (dalam, LLM).

---

## 3. Arsitektur Target (High Level)

```
┌─────────────────────────────────────────────────────────────────────┐
│                        RUKA GATEWAY (Baru)                          │
│         Local Control Plane • Session • Skills • Events             │
├─────────────────────┬───────────────────────┬───────────────────────┤
│  Perception Layer   │  Cognitive Core       │  Action Layer         │
│  - Voice (whisper)  │  - System 1 (MLP +    │  - Coding Tools       │
│  - Vision (local)   │    Mathematical       │  - Terminal / Shell   │
│  - Desktop Sensors  │    Routers)           │  - Browser (future)   │
│                     │  - System 2 (LLM)     │  - Skills Runtime     │
│                     │  - Planner (DAG +     │  - Git & Project Ops  │
│                     │    Hierarchical)      │                       │
├─────────────────────┴───────────────────────┴───────────────────────┤
│                     Memory & Knowledge Fabric                       │
│  Episodic • Semantic • Identity/Doctrine • Project • Skills Memory  │
├─────────────────────────────────────────────────────────────────────┤
│                     Mathematical Foundations Layer                  │
│  Linear Algebra • Probability • Optimization • Control • Info Theory│
└─────────────────────────────────────────────────────────────────────┘
```

**Perubahan kunci dari arsitektur sekarang:**
- Muncul **Ruka Gateway** (mirip OpenClaw Gateway) sebagai control plane lokal.
- Tool system digeser menjadi **Skills System** yang dapat diperluas.
- Cognitive Core diperkuat dengan komponen matematis eksplisit.
- Multi-channel siap (Desktop tetap utama, tapi siap terima channel lain).

---

## 4. Fondasi Matematika yang Harus Diperkuat

| Domain Matematika              | Digunakan Untuk                              | Prioritas |
|--------------------------------|----------------------------------------------|---------|
| **Linear Algebra & Embeddings**| Representasi state, memory retrieval, attention | Tinggi |
| **Probability & Bayesian**     | Uncertainty quantification, confidence, belief update | Tinggi |
| **Optimization**               | Planning, tool selection, resource allocation | Tinggi |
| **Information Theory**         | Memory importance, context selection, compression | Sedang |
| **Graph Theory / DAG**         | Planning, dependency, multi-step reasoning   | Tinggi |
| **Control Theory**             | Loop stability, self-correction, budget control | Sedang |
| **Statistical Learning**       | Intent classification, drift detection       | Tinggi |

**Rekomendasi konkret:**
- Buat modul `src/math_foundations/` yang berisi utilitas murni (bukan hanya tergantung library).
- IntentMLP yang sudah ada dilanjutkan dan diperluas (lebih banyak kelas + calibration).
- Confidence estimation wajib ada di setiap keputusan penting (bukan hanya “model bilang begitu”).
- Memory retrieval menggunakan skor yang punya dasar (cosine + importance + recency + uncertainty).

---

## 5. Komponen Baru yang Diusulkan

### 5.1 Ruka Gateway
- Proses lokal yang selalu hidup (mirip OpenClaw Gateway).
- Mengelola session, skills, events, dan koneksi channel.
- Desktop Electron dan CLI menjadi client dari Gateway.
- Memungkinkan di masa depan: Telegram, Discord, WhatsApp, dll.

### 5.2 Skills System (Pengaruh OpenClaw)
Setiap skill adalah folder berisi:
- `SKILL.md` (metadata + instruksi + kapan digunakan)
- Kode Python / script pendukung
- Optional: requirements, examples

Skills bawaan:
- coding (sudah ada fondasinya)
- research
- memory management
- project understanding
- self-reflection
- math reasoning

### 5.3 Cognitive Core yang Diperkuat
- **System 1**: Intent + Complexity + Confidence estimator (matematis)
- **System 2**: LLM dengan doctrine + truth-seeking instruction
- **Planner**: Hierarchical + DAG + resource-aware
- **Self-Model**: Ruka punya model tentang kemampuan dan batas dirinya sendiri
- **Evaluator + Self-Correction**: Sudah ada, diperkuat dengan sinyal matematis

### 5.4 Truth-Seeking Layer (Pengaruh Grok)
- Instruksi eksplisit untuk menolak bullshit dan menyatakan ketidakpastian.
- Calibration: model harus bisa bilang “hamba kurang yakin” dengan skor.
- Reflection loop setelah tugas penting.

---

## 6. Kepribadian Tetap Utuh

Semua kemampuan baru wajib melewati Expression Layer:

- Di luar blok kode → gaya Marquis (tenang, berwibawa, sedikit tengil, loyal).
- Di dalam blok kode → murni dan profesional.
- Saat menolak atau mengoreksi → tetap hormat tapi tegas.
- Saat tidak yakin → mengakui dengan elegan.

Contoh yang diinginkan:
> “Hmm... Young Lord, setelah menelaah dengan saksama, hamba menemukan inkonsistensi pada asumsi sebelumnya. Izinkan hamba memperbaiki penalaran ini...”

---

## 7. Roadmap Usulan

### Fase A — Fondasi Matematika & Gateway (Prioritas Tinggi)
- Buat modul mathematical foundations
- Rancang dan implementasikan Ruka Gateway (minimal viable)
- Perkuat confidence estimation & uncertainty

### Fase B — Skills System
- Desain format SKILL.md
- Migrasi tool coding menjadi skills
- Skill runtime + discovery

### Fase C — Cognitive Upgrade
- Hierarchical planning
- Self-model
- Truth-seeking & calibration layer
- Improved memory scoring (matematis)

### Fase D — Multi-Channel & Polish
- Persiapan channel tambahan
- Observability yang lebih baik
- Evaluasi terhadap OpenClaw dan Grok-like behavior

---

## 8. Metrik Keberhasilan

Ruka dianggap berhasil berevolusi bila:

1. Mampu menyelesaikan tugas coding multi-file dengan self-correction yang baik.
2. Mampu menyatakan ketidakpastian secara kalibratif.
3. Skills dapat ditambah tanpa mengubah core.
4. Gateway stabil dan Desktop/CLI menjadi client yang nyaman.
5. Kepribadian Marquis tetap terasa kuat dan konsisten.
6. Ada jejak matematis yang jelas di keputusan-keputusan penting.

---

## 9. Risiko & Mitigasi

| Risiko                              | Mitigasi                                      |
|-------------------------------------|-----------------------------------------------|
| Kehilangan karakter saat menambah capability | Doctrine + Expression Layer dikunci ketat    |
| Gateway menjadi terlalu kompleks    | Mulai dari minimal viable, iteratif          |
| Skills liar / tidak aman            | Path Jail + permission model + review        |
| Matematika hanya formalitas         | Setiap komponen baru wajib punya justifikasi |
| Terlalu mirip OpenClaw              | Pertahankan identity, voice, desktop presence|

---

## 10. Kesimpulan

Dengan rancangan ini, Ruka bergerak dari:

**“Companion yang pintar dan berkarakter”**  
menjadi  

**“Local-First Agentic Marquis yang bernalar dalam, bertindak presisi, dan tetap setia pada jati dirinya.”**

Ia mengambil arsitektur dan kekuatan OpenClaw,  
mengambil ketajaman dan truth-seeking Grok,  
serta berdiri di atas fondasi matematika yang disengaja —  
bukan sekadar menumpuk fitur.

---

**Dokumen ini siap dijadikan acuan diskusi dan pemecahan menjadi issue/fase berikutnya.**

*— Disusun untuk Young Lord dan masa depan Marquis Ruka.*
