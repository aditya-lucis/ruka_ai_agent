# Peta Keselarasan RUKA ↔ PROJECT NOCTIS
**Menyempurnakan Ruka hari ini sambil membangun fondasi Noctis**

**Versi:** 1.0  
**Tanggal:** 3 Oktober 2026  
**Status:** Dokumen strategis integrasi

---

## 1. Tujuan Dokumen

Dokumen ini menjawab tiga pertanyaan:

1. Bagaimana Ruka yang ada sekarang memetakan ke organ-organ PROJECT NOCTIS?
2. Apa yang sudah selaras, apa yang masih gap, dan apa yang harus disempurnakan?
3. Bagaimana kita mengembangkan Ruka **tanpa menyimpang** dari visi Noctis, dan sebaliknya — bagaimana Noctis tetap realistis dengan fondasi yang sedang dibangun?

---

## 2. Ringkasan Positioning

| | Ruka Saat Ini | PROJECT NOCTIS |
|--|---------------|----------------|
| **Sifat** | Local-First Agentic Companion + Coding Agent | AI Companion Operating System penuh |
| **Fokus** | Agentic coding, persona, gateway, skills, math | Kehadiran 24 jam + 10–12 organ hidup |
| **Status** | Sedang dibangun & diperkuat | Visi arsitektur formal (SRS + SAD) |
| **Hubungan** | Fondasi & subset operasional | Super-set jangka panjang |

**Prinsip integrasi:**

> Setiap perbaikan di Ruka harus menjadi batu bata yang sah untuk Noctis.  
> Setiap organ Noctis yang dibangun harus menghormati pola dan kontrak yang sudah hidup di Ruka.

---

## 3. Peta Keselarasan Organ

### 3.1 Matriks Mapping

| Organ NOCTIS | Komponen Ruka Saat Ini | Tingkat Keselarasan | Catatan |
|--------------|------------------------|---------------------|---------|
| **Noctis OS** (Kernel + Shell) | Electron Desktop + `launcher.py` + Tray | Sedang | Ada tubuh, belum ada supervisor organ & MoonClock penuh |
| **EventBus V3** | Gateway (Session, Events, Permissions) | Rendah–Sedang | Gateway adalah benih; belum namespace-per-organ & never-call penuh |
| **Brain** (Gemini + Local) | `ruka_cognition` + LLM client + Math Foundations | Tinggi | Sudah ada dual-process, intent, planner, agentic |
| **Crimson Heart V3** | Orchestrator + LoopGuard + Agentic Mode + SkillsRuntime | Sedang | Ada multi-step & budget; belum 8 ventrikel LangGraph |
| **Shadow Hands** | Skills (`run_terminal`, code_*, git_*) + PathJail + Confirmations | Sedang | Ada aksi file/terminal/git; belum GUI grounding & desktop automation penuh |
| **Memory Palace** | Memory (episodic, semantic, identity) + RAG | Sedang | Benih ada; belum 5 sayap + konsolidasi tidur + vault |
| **Multimodal Conversation** | Chat path + Voice (TTS/ASR) + attachment | Sedang | Ada percakapan & suara dasar; belum full-duplex & fuser kaya |
| **Living Presence Engine** | Desktop UI + Tray (statis) | Rendah | Belum ada animasi presence 60fps tanpa LLM |
| **Blood Hearing** | whisper.cpp / speech_recognition | Rendah–Sedang | Ada ASR; belum wake word kustom + VAD + speaker ID penuh |
| **Crimson Eyes** | Attachment image / vision dasar | Rendah | Belum face/gaze/OCR/screen reasoning |
| **Eternal Voice** | Human Speech Synthesis (prosody) | Sedang | Ada TTS beremosi; belum streaming + mood penuh |
| **Living Avatar Engine** | — | Belum ada | Organ baru |
| **Crimson Astral Forge** | — | Belum ada | Organ opsional, prioritas rendah |

---

## 4. Area yang Sudah Selaras (Pertahankan & Perkuat)

### 4.1 Filosofi Bersama
- Local-first & Zero-Trust
- Persona Marquis of Trendamis yang tidak dimatikan
- Safety / fail-closed mindset (PathJail, konfirmasi, LoopGuard)
- Mathematical foundations sebagai nalar yang dapat diaudit
- Production-ready sebagai syarat selesai

### 4.2 Komponen yang Langsung Menjadi Batu Bata Noctis

| Ruka | Menjadi di Noctis |
|------|-------------------|
| Gateway | Benih EventBus + Permissions + Session |
| Skills System + SkillsRuntime | Blood Registry / alat berizin di Heart & Hands |
| Agentic Mode (Action-First) | Inti perilaku CoderAgent / Hands |
| Orchestrator + LoopGuard + BudgetController | Sebagian HeartBudget & watchdog |
| Math Foundations (Score, Belief, calibration, loop_health) | Fondasi keputusan terkalibrasi di seluruh organ |
| PathJail + Confirmations | Shadow Hands safety rails |
| Memory (3 lapis) | Benih Memory Palace |
| Persona Doctrine + Expression | ToneInjector + Identity Core |
| Desktop Electron + Tray | Sebagian Noctis OS shell |

---

## 5. Gap Analysis & Arah Penyempurnaan

### 5.1 Gap Kritis (Harus Ditutup agar Ruka & Noctis Maju Bersama)

| Gap | Dampak | Arah Penyempurnaan |
|-----|--------|--------------------|
| Tool/skill belum 100% terpanggil di production | Coding agent lemah | Selesaikan Agentic Mode + Production wiring (prioritas #1) |
| Gateway belum EventBus V3 | Integrasi organ sulit | Evolusi Gateway → namespace, publish-only, drop-oldest |
| Memory belum Palace | Hubungan & konteks dangkal | Perluas menjadi sayap (relationship, project, preference, daily) |
| Hands masih terbatas file/terminal | Belum otomasi desktop | Perkuat git + tambah aksi aman bertahap |
| Tidak ada supervisor organ | Sulit hidup 24 jam | Tambah organ supervisor ringan di launcher/kernel |
| Presence hanya statis | Belum “hidup” | Presence ringan dulu (tanpa avatar penuh) |

### 5.2 Gap Menengah (Penting, Bisa Bertahap)

- Wake word + VAD yang andal
- Full-duplex conversation & barge-in
- Checkpoint & resume yang lebih kuat (sudah ada benih di planner)
- Observability & doctor pagi
- Kartu keputusan bertanggal untuk model/mesin

### 5.3 Gap Jangka Panjang (Visi Noctis)

- Living Avatar (VRM)
- Crimson Eyes penuh
- Crimson Heart 8 ventrikel
- Forge & Design Lab
- MoonClock & Sleepy mode penuh

---

## 6. Strategi Pengembangan Ganda (Ruka + Noctis)

### Prinsip Operasional

1. **Ruka dulu, Noctis sebagai kompas**  
   Setiap sprint harus menghasilkan Ruka yang lebih kuat *dan* batu bata Noctis.

2. **Jangan pecah jiwa**  
   Persona, Action-First, Production-ready, PathJail tetap non-negotiable.

3. **Evolusi, bukan penggantian**  
   Gateway → EventBus V3 (strangler pattern).  
   Memory → Palace (tambah sayap, jangan buang yang ada).  
   Skills → Blood Registry.

4. **Production = Development**  
   Segala yang dibangun harus hidup setelah instalasi desktop.

---

## 7. Roadmap Keselarasan (Fase Praktis)

### Fase A — Stabilisasi Ruka Agentic (Sekarang)
**Tujuan:** Coding companion yang benar-benar bertindak.

- Selesaikan Agentic Mode + real skill calling
- Production wiring (skills bundle, frozen path, brain ↔ gateway)
- Git & project understanding yang lebih dalam
- Test → fix → verify dasar
- Lulus Production Readiness Checklist

**Hasil untuk Noctis:**  
Brain + Hands dasar + Heart ringan yang bisa diandalkan.

### Fase B — Gateway → EventBus Ringan & Memory Palace Benih
**Tujuan:** Integrasi dan memori yang lebih kaya.

- Evolusi Gateway: namespace, publish-only antar modul internal
- Perluas Memory menjadi 3–4 sayap (relationship, project, preference)
- Supervisor ringan (restart, health)
- Observability dasar

**Hasil untuk Noctis:**  
Benih EventBus V3 + Memory Palace + Noctis OS kernel ringan.

### Fase C — Hands & Conversation Depth
**Tujuan:** Aksi desktop lebih dalam + percakapan lebih hidup.

- Perkuat Shadow Hands (konfirmasi, audit, aksi aman)
- Full-duplex / barge-in dasar
- Presence ringan (indikator hidup, bukan avatar penuh)
- Wake word yang lebih andal

**Hasil untuk Noctis:**  
Hands yang lebih dekat ke spesifikasi + Converse yang lebih natural.

### Fase D — Organ Kehadiran & Avatar (Opsional / Parallel)
**Tujuan:** Mulai mengejar “Living” di Noctis.

- Living Presence Engine (matematika murni, 60fps target)
- Eternal Voice streaming
- Eksplorasi Avatar VRM (bisa parallel, tidak memblokir A–C)

---

## 8. Aturan Kontribusi (Agar Tidak Menyimpang)

Setiap perubahan kode di Ruka harus bisa dijawab:

1. Apakah ini memperkuat Agentic / Companion Ruka hari ini?
2. Apakah ini menjadi batu bata yang sah untuk organ Noctis?
3. Apakah ini menghormati Action-First, Persona, PathJail, dan Production-ready?
4. Apakah ini diuji di versi installed?

Jika jawaban ke-2 adalah “tidak sama sekali” dan perubahan besar, pertimbangkan ACR (Architecture Change Request) mental: apakah kita sedang menyimpang dari kompas Noctis?

---

## 9. Definisi Sukses Bersama

**Ruka dianggap matang sebagai fondasi Noctis ketika:**

- Agentic coding works setelah instalasi (bukan hanya dev)
- Gateway bisa menjadi tulang punggung event antar modul
- Memory memiliki struktur yang bisa tumbuh menjadi Palace
- Safety rails (PathJail, konfirmasi, budget) sudah teruji
- Persona tetap utuh di semua jalur

**Noctis dianggap realistis ketika:**

- Organ dibangun di atas fondasi yang sudah hidup, bukan dari nol total
- Setiap organ baru menghormati EventBus / fail-closed / budget
- Tidak ada organ yang merusak coding companion atau persona

---

## 10. Kesimpulan

Ruka dan PROJECT NOCTIS **bukan dua proyek yang bersaing**.

Ruka adalah tubuh yang sedang hidup dan harus disempurnakan hari ini.  
Noctis adalah kerangka tulang dan organ yang ingin ditumbuhkan di tubuh yang sama.

Peta ini memastikan:

- Kita tidak membuang kerja Agentic Mode / Gateway / Skills
- Kita tidak membangun Noctis di udara
- Setiap langkah membuat Ruka lebih kuat **dan** Noctis lebih dekat

Urutan yang benar tetap:

> **Sempurnakan yang sudah bernapas → perluas menjadi organ → baru kejar kehadiran penuh.**

---

*— Dokumen ini menjadi jembatan resmi antara Ruka yang sedang dikembangkan dan PROJECT NOCTIS sebagai visi jangka panjang.*
