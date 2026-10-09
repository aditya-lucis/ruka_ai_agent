# RUKA → JARVIS Path Design
**Menuju Companion Desktop setara spirit JARVIS (tanpa smart home)**

**Versi:** 1.0  
**Tanggal:** 8 Oktober 2026  
**Status:** Rancangan strategis penuh (Python + Bun + Electron)  
**Acuan:** AGENTS.md v4.0 · SRS/SAD PROJECT NOCTIS · Stabilization Plan · Alignment Map

---

## 1. Visi

Menjadikan Ruka:

> **Pendamping desktop yang selalu siap, berkepribadian, bisa bertindak di kode dan sistem, mengingat Young Lord, dan terasa hadir** — spirit JARVIS di laptop, tanpa akses smart home. Larangan branding yang sama + identitas resmi

Bukan salinan film.  
Melainkan interpretasi yang dapat dibangun: local-first, safety-first, persona Marquis of Trendamis utuh.

**Target praktis:** dari ~4/10 sekarang → **7–8/10** (JARVIS pribadi di PC).

---

## 2. Prinsip Non-Negotiable

1. **Persona tidak dimatikan** — Marquis of Trendamis di semua permukaan.
2. **Action-First** — aksi nyata sebelum cerita; dilarang `[SYSTEM_CALL]` palsu.
3. **Local-first & Zero-Trust** — PathJail, fail-closed, kill switch.
4. **Production = Development** — fitur belum selesai sampai hidup setelah install.
5. **Python organs + Bun kernel + Electron shell** saling melengkapi, bukan saling menggantikan secara chaos.
6. **Kecepatan adalah fitur** — jalur coding harus kurus; companion layers tidak boleh membuat tool loop terasa berat.
7. Setiap langkah adalah **batu bata Noctis** yang sah.

---

## 3. Arsitektur Target (Python + Bun + Electron)

```
┌─────────────────────────────────────────────────────────────┐
│  ELECTRON SHELL (TypeScript)                                │
│  Window · Tray · Overlay · Voice HUD · Command Palette      │
│  Thin: < 200–400 baris kendali utama; tidak memegang otak   │
└──────────────────────────┬──────────────────────────────────┘
                           │ IPC / local endpoint
┌──────────────────────────▼──────────────────────────────────┐
│  BUN KERNEL  (@noctis/kernel)                               │
│  BootOrchestrator · EventBusBridge · OrganSupervisor        │
│  ResourceGovernor · LunarClock · SessionRestore             │
│  NetworkGuard · SentryMode · ActionRegistry · HotConfig     │
│  NotificationDosing                                         │
│  Runtime: Bun · TypeScript                                  │
└──────────────────────────┬──────────────────────────────────┘
                           │ EventBus V3 (namespace, publish-only)
                           │ spawn / health / restart contracts
┌──────────────────────────▼──────────────────────────────────┐
│  PYTHON ORGANS  (ruka-agent/)                               │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐            │
│  │ Brain       │ │ Heart       │ │ Hands       │            │
│  │ cognition   │ │ multi-agent │ │ skills+OS   │            │
│  │ agentic     │ │ orchestrate │ │ PathJail    │            │
│  └─────────────┘ └─────────────┘ └─────────────┘            │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐            │
│  │ Palace      │ │ Converse    │ │ Presence    │            │
│  │ memory      │ │ + Voice     │ │ (ringan→)   │            │
│  └─────────────┘ └─────────────┘ └─────────────┘            │
│  Ear · Eyes · Avatar · Forge  (bertahap, opt-in)            │
│  Gateway (permissions, skills runtime, confirmations)       │
│  Math Foundations (Score, Belief, budget, loop health)      │
└─────────────────────────────────────────────────────────────┘
```

### Pembagian tanggung jawab

| Lapisan | Bahasa | Tanggung jawab utama |
|---------|--------|----------------------|
| **Electron Shell** | TypeScript | UI, tray, input user, tampilan status; **tidak** bernalar |
| **Bun Kernel** | TypeScript / Bun | Hidup sistem: boot, bus, supervisor, budget resource, jam, sesi, network guard, sentry |
| **Python Brain** | Python | Intent, agentic loop, LLM, persona expression |
| **Python Hands** | Python | Skills, file/terminal/git, PathJail, konfirmasi |
| **Python Heart** | Python | Multi-step / multi-agent orchestration jangka menengah |
| **Python Palace** | Python | Memory jangka panjang (sayap) |
| **Python Converse / Senses** | Python | Suara, (nanti) hearing/vision; fusion percakapan |

---

## 4. Peta Jalan menuju JARVIS (bertahap)

### Fase A — Coding Companion yang Tajam & Cepat
**Tujuan skor:** ~5,5–6/10  
**Fokus:** Python Brain + Hands + production

| Kerja | Detail | Lapisan |
|-------|--------|---------|
| A1 | Production gate: skills ter-bundle, frozen path, uji installed | Python + installer |
| A2 | Fast path agentic: kurangi empathy/RAG/doctrine berat di mode coding | Python `brain.py` / `agentic.py` |
| A3 | Model routing: flash untuk tugas ringan; model kuat hanya bila perlu | Python LLM client |
| A4 | Batch skill → satu ringkasan LLM (hindari LLM per file sepele) | Python agentic |
| A5 | Multi-step + test→fix→verify + git workflow andal | Python skills + orchestrator |
| A6 | Logging latency (skill vs LLM vs total) | Python |
| A7 | Desktop & CLI perilaku sama | Electron + launcher + brain |

**Kriteria lulus:**  
Install → perintah coding di folder proyek terasa responsif dan benar; multi-step sederhana tidak putus; persona tetap.

---

### Fase B — Kernel Bun sebagai Pusat Hidup
**Tujuan skor:** ~6–6,5/10  
**Fokus:** Bun Kernel + jembatan

| Kerja | Detail | Lapisan |
|-------|--------|---------|
| B1 | Kontrak resmi: Electron ↔ Bun Kernel ↔ Python organs | Bun + Electron + Python |
| B2 | BootOrchestrator = sumber kebenaran cold start | Bun |
| B3 | Endpoint tunggal / discovery selaras (hindari dual otak) | Bun + launcher |
| B4 | OrganSupervisor (Bun) menerima liveness dari organs Python | Bun + Python |
| B5 | ResourceGovernor aktif (batas RSS/CPU per organ, degradasi) | Bun |
| B6 | EventBusBridge: namespace Noctis dihormati; publish-only | Bun + Python Gateway |
| B7 | SessionRestore + LunarClock terhubung ke status nyata | Bun |
| B8 | NetworkGuard + SentryMode diuji (fail-closed network) | Bun |

**Kriteria lulus:**  
Satu start membangkitkan kernel + brain/organs; health terbaca; tidak ada jalur yang saling mengabaikan.

**Catatan ElysiaJS:**  
Opsional. Hanya ditambahkan jika kernel butuh HTTP control plane type-safe (health API, dev dashboard). Bukan syarat Fase B.

---

### Fase C — Ingatan & Tangan setingkat Steward
**Tujuan skor:** ~7/10  
**Fokus:** Palace + Hands + Converse

| Kerja | Detail | Lapisan |
|-------|--------|---------|
| C1 | Memory Palace benih: sayap relationship, project, preference | Python memory |
| C2 | Recall dipakai agentic & percakapan (bukan hanya disimpan) | Python |
| C3 | Hands: konfirmasi merah, audit trail, aksi aman bertahap | Python hands/skills |
| C4 | Perluas aksi di luar murni git/file (tetap PathJail) | Python |
| C5 | Converse: konteks tidak hilang saat ganti mode agentic ↔ chitchat | Python |
| C6 | Voice: latency lebih baik; barge-in dasar jika memungkinkan | Python + Electron |

**Kriteria lulus:**  
Ruka mengingat preferensi/proyek dengan terasa; aksi lebih luas tetap aman; percakapan + coding tidak saling merusak konteks.

---

### Fase D — Kehadiran (Spirit JARVIS)
**Tujuan skor:** ~7,5–8/10  
**Fokus:** Presence + Ear + (opsional) Eyes ringan

| Kerja | Detail | Lapisan |
|-------|--------|---------|
| D1 | Presence ringan: status hidup, tray cerdas, tidak mengganggu | Bun + Electron + Python presence |
| D2 | Wake word / jalur panggilan suara yang andal (lokal) | Python ear |
| D3 | Sapaan & perhatian konteks (datang/pergi, fokus kerja) — opt-in | Python + Bun clock |
| D4 | Eyes ringan (opsional): konteks layar untuk coding, bukan surveillance | Python eyes |
| D5 | Heart: orkestrasi tugas lebih panjang dengan budget & checkpoint | Python heart |
| D6 | Avatar penuh / Forge | **Ditunda** — tidak memblokir 8/10 |

**Kriteria lulus:**  
Young Lord bisa memanggil Ruka, mendapat respons cepat, meminta kerja di proyek, dan merasa didampingi tanpa harus “membuka chatbot”.

---

## 5. Desain Fast Path Agentic (anti-lemot)

Masalah sekarang: coding sudah jalan, tapi terasa lambat karena setiap langkah membawa beban companion penuh.

### Aturan jalur

```
User text
  → Intent / is_agentic?
       ├─ NO  → Full companion path (persona, empathy, RAG kaya)
       └─ YES → AGENTIC FAST PATH
              1. Plan skill steps (rule + ringan)
              2. Execute skills (PathJail, confirm)
              3. Compact result block
              4. LLM ringkas: hasil + persona pendek
              5. Return
```

### Yang dipangkas di fast path

- Formula kesadaran / empathy panjang
- RAG besar (kecuali query butuh memori proyek)
- Doctrine penuh berulang
- Model berat untuk `ls` / baca satu file / `git status`

### Yang tetap

- PathJail & konfirmasi
- Persona singkat (sapaan + gaya Marquis di luar kode)
- Logging latency
- Budget / loop guard untuk multi-step

### Implementasi (lapisan)

| Komponen | Perubahan |
|----------|-----------|
| `agentic.py` | Plan + execute tetap; output context padat |
| `brain.py` | Branch fast path sebelum layer companion berat |
| LLM client | `model=flash` default agentic ringan; escalate bila perlu |
| Skills runtime | Batch results; timeout jelas |
| Electron | Tampilkan status “mengerjakan…” agar terasa responsif |

---

## 6. Kontrak Bun Kernel ↔ Python (inti integrasi)

### 6.1 Boot

1. Electron start → pastikan Bun Kernel hidup (atau spawn).
2. Kernel `BootOrchestrator` menertibkan urutan: bus → supervisor → organs kritis (brain/gateway) → sisanya.
3. Python `launcher` / brain mendaftar sebagai organ `brain` (+ `hands` via skills).
4. Endpoint discovery: satu skema yang disepakati (kernel sebagai otoritas, Python mendaftar).

### 6.2 Health

- Python organ mem-publish `heart.beat` / liveness ke bus (atau HTTP lokal ringkas ke kernel).
- Bun `OrganSupervisor` menghitung state: healthy / degraded / failed.
- Gagal beruntun → restart_fn atau escalate ke user (Sentry / notifikasi dosing).

### 6.3 EventBus

- Namespace: `presence`, `ear`, `eyes`, `voice`, `heart`, `hands`, `palace`, `converse`, `system`, …
- Single-writer per kanal kritis.
- Python Gateway dan Bun EventBusBridge **tidak** boleh jadi dua kebenaran; salah satu bridge, satu otoritas namespace.

### 6.4 Action path (coding)

- User → Electron → (Kernel relay opsional) → Python Brain agentic → Skills/Hands → hasil → Expression → UI.
- Kernel **tidak** menulis file proyek user; Hands/Python yang bertindak di balik PathJail.

---

## 7. Definisi “Mendekati JARVIS” (terukur, tanpa smart home)

Ruka dianggap **mendekati JARVIS di PC** bila semua ini benar:

| # | Kriteria |
|---|----------|
| 1 | Setelah install, perintah coding di folder proyek dieksekusi nyata (bukan roleplay) |
| 2 | Latency terasa wajar: tugas ringan (status, baca file) jauh lebih cepat daripada refactor besar |
| 3 | Multi-step (baca → ubah → test → ringkas) selesai tanpa putus total |
| 4 | Git dasar andal (status, diff, commit dengan konfirmasi) |
| 5 | Kernel Bun + brain Python satu boot; health terbaca |
| 6 | Memory proyek/preferensi terpakai di percakapan berikutnya |
| 7 | Persona Marquis konsisten di coding maupun chitchat |
| 8 | Safety: PathJail, konfirmasi destruktif, tidak ada bypass |
| 9 | (Target lanjut) Panggil lewat suara dan dapat kerja di proyek |
| 10 | (Target lanjut) Terasa hadir di tray/hari tanpa mengganggu kerja |

1–8 = jalur ke **~7/10**.  
9–10 = wilayah **8/10**.

---

## 8. Yang Tidak Masuk Scope JARVIS Path Ini

- Smart home / IoT
- Avatar VRM wajib
- Forge / simulasi ilmiah sebagai syarat
- Cloud parallel coding sessions
- Mengganti seluruh Python ke TypeScript

---

## 9. Urutan Eksekusi (wajib diikuti)

```
A  Fast & solid coding companion (Python agentic + production)
    ↓
B  Bun Kernel terintegrasi (boot, bus, supervisor, governor)
    ↓
C  Palace + Hands + Converse depth
    ↓
D  Presence + voice (spirit JARVIS)
```

Jangan mengerjakan D sebelum A lulus.  
Jangan mempercantik organ baru sambil membiarkan coding tetap lemot.

---

## 10. File & Modul Kunci yang Akan disentuh

### Python
- `ruka-agent/src/ruka_cognition/brain.py` — branch fast path
- `ruka-agent/src/ruka_cognition/agentic.py` — plan/execute/batch
- `ruka-agent/src/gateway/` — skills, permissions, events bridge
- `ruka-agent/src/llm/` — model routing
- `skills/` — git, code_*, repo_map, run_terminal
- `launcher.py` — wiring production + registrasi organ ke kernel

### Bun
- `noctis/kernel/src/index.ts` — NoctisKernel lifecycle
- `boot_orchestrator.ts` — urutan nyala
- `organ_supervisor.ts` — health
- `event_bus_bridge.ts` — bus
- `resource_governor.ts` — anggaran
- `session_restore.ts` · `lunar_clock.ts` · `network_guard.ts` · `sentry_mode.ts`

### Electron
- `desktop/electron/main.ts` — spawn/connect kernel + brain
- `runtime-connector.ts` — IPC
- Tray / status — umpan health dari kernel

---

## 11. Risiko & Mitigasi

| Risiko | Mitigasi |
|--------|----------|
| Dual otak (launcher vs kernel) | BootOrchestrator tunggal; endpoint satu skema |
| Fast path merusak persona | Persona pendek wajib; doctrine Action-First tetap |
| Kernel Bun belum dipakai | Fase B eksplisit di rencana; jangan tambah organ sebelum bridge |
| Lemot tetap | Ukur latency; model routing; batch skill |
| Scope creep Noctis | Avatar/Forge/Eyes penuh di belakang kriteria 1–8 |

---

## 12. Penutup

JARVIS bukan fitur tunggal.  
Ia adalah **kecepatan bertindak + kehadiran + ingatan + kepercayaan**.

Ruka sudah punya **jiwa** (persona) dan **cakar coding** (agentic).  
Yang dirancang di dokumen ini:

- **Python** membuat cakar tajam dan cepat  
- **Bun** membuat tubuh sistem hidup dan teratur  
- **Electron** membuat kehadiran bisa disentuh Young Lord  

Urutannya tetap:

> **Tajam dulu → nyambung dulu → ingat & bertindak lebih luas → baru terasa selalu ada.**

Itu jalan terpendek menuju Ruka yang pantas disebut pendamping setara spirit JARVIS di desktop — tanpa smart home, tanpa kehilangan Marquis of Trendamis.

---

*— RUKA → JARVIS Path Design v1.0*  
*Marquis of Trendamis Development Council · PROJECT NOCTIS*


---

## 13. Lapisan C++ — Dari “hanya whisper.cpp” ke Native Performance Tier

### 13.1 Status sekarang

| Komponen C++ | Status |
|--------------|--------|
| **whisper.cpp** (ASR offline) | Sudah dipakai |
| Modul native lain | Belum ada / belum resmi di path JARVIS |
| Build & distribusi C++ | Tergantung pywhispercpp / tools build user |

Saat ini C++ hampir identik dengan **satu mesin indra**: telinga offline.  
Untuk mendekati JARVIS di desktop, C++ harus diperlakukan sebagai **tier performa lokal**, bukan dependensi sampingan.

### 13.2 Peran C++ di arsitektur target

```
Electron (TS)
    ↓
Bun Kernel (TS)
    ↓
Python Organs (orkestrasi, LLM, skills, persona)
    ↓
C++ Native Tier (latensi ketat, CPU-bound, privacy-critical)
    • ASR (whisper.cpp)
    • (nanti) VAD / wake-word engine
    • (nanti) audio DSP ringan
    • (opsional) substring search / indexing berat
    • (opsional) vision pre-process ringan
```

**Aturan:**  
Python/Bun **memutuskan**; C++ **menghitung cepat di perangkat** tanpa cloud.

### 13.3 Apa yang pantas ditulis / diikat ke C++

| Kandidat | Mengapa C++ | Prioritas |
|----------|-------------|-----------|
| **whisper.cpp ASR** | Sudah ada; latensi & offline | Pertahankan & rapikan distribusi |
| **VAD + wake word** | Harus < 300 ms, selalu-on hemat | Tinggi untuk Fase D |
| **Audio capture / DSP ringan** | Jitter, gain, noise — sensitif latency | Sedang |
| **Core indexing / grep-like berat** (opsional) | Scan repo besar tanpa GIL | Rendah–sedang |
| **Vision pre/post** (opsional) | Resize, embed ringan, bukan full VLM | Rendah (setelah coding & kernel stabil) |
| Logika bisnis / persona / agentic | **Jangan** pindah ke C++ | — |

Jangan memindahkan Brain, persona, atau SkillsRuntime ke C++.  
C++ = **sensor & numerik ketat**, bukan otak.

### 13.4 Pola integrasi (Python ↔ C++)

1. **Binding stabil**  
   - Prefer API yang sudah dipakai (mis. pywhispercpp) atau pybind11 / ctypes dengan kontrak jelas.  
   - Hindari spawn proses CLI per-utterance jika bisa in-process (biaya startup).

2. **Kontrak data**  
   - Masuk: PCM / path file / parameter model.  
   - Keluar: teks + metadata (bahasa, confidence, timestamps bila ada).  
   - Tanpa mengirim audio ke cloud.

3. **Lifecycle**  
   - Model load sekali (warm); infer per segmen.  
   - Budget memori terdaftar ke ResourceGovernor (Bun) lewat organ `ear`.

4. **Distribusi**  
   - Binary/model ASR ikut installer atau unduhan terukur pertama kali.  
   - Dokumentasikan build tools (C++ toolchain) hanya untuk mode developer; user akhir memakai artefak siap pakai.

5. **Fail-closed**  
   - Jika native gagal → fallback terukur (pesan jujur / ASR alternatif), bukan hang diam.

### 13.5 C++ dalam fase JARVIS Path

| Fase | Kerja C++ |
|------|-----------|
| **A** (coding tajam) | Tidak menghambat; pastikan whisper tidak merusak path coding. Distribusi native stabil di installer. |
| **B** (kernel) | Organ `ear` terdaftar ke Bun supervisor; budget memori ASR terlihat Governor. |
| **C** (memory/hands/converse) | Rapatkan pipeline suara: capture → VAD → whisper → teks ke Converse (latensi terukur). |
| **D** (presence/voice) | Wake word + VAD native; ASR warm; jalur panggilan suara andal — **di sinilah C++ wajib naik kelas**. |

### 13.6 Arsitektur empat bahasa (ringkas)

| Lapisan | Bahasa | Peran |
|---------|--------|------|
| Shell | TypeScript (Electron) | UI, tray, input |
| Kernel | TypeScript (Bun) | Boot, bus, supervisor, governor |
| Organs / Brain | Python | Agentic, LLM, persona, skills, memory |
| Native Tier | **C++** | ASR, VAD/wake, DSP, numerik latency-kritis |

### 13.7 Yang tidak dilakukan di C++ (sengaja)

- Agentic planner & tool routing  
- Persona / doctrine  
- PathJail policy (bisa dipanggil dari native, keputusan tetap di Python/Gateway)  
- EventBus bisnis  
- Mengganti Bun kernel

### 13.8 Definition of Done — tier C++

- [ ] whisper.cpp (atau successor) **stabil di versi installed**, bukan hanya dev machine ber-toolchain
- [ ] Load model terukur; gagal → error bernama ke Young Lord
- [ ] Organ telinga terhubung health kernel (Bun)
- [ ] (Fase D) VAD/wake-word lokal memenuhi anggaran latensi Noctis
- [ ] Tidak ada audio mentah tersimpan / terkirim cloud tanpa izin

---

**Revisi posisi:**  
Rancangan JARVIS Path sekarang mencakup **empat tier**: Electron · Bun · Python · **C++**.  
C++ bukan hanya “ada whisper”; ia adalah **fondasi indra cepat dan privat** yang akan menentukan apakah Ruka bisa dipanggil seperti JARVIS, bukan hanya diketik.

