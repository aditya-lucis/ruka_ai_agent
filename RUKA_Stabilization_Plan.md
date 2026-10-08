# Rencana Stabilisasi Ruka → Noctis
**Dari yang paling krusial**

**Versi:** 1.0  
**Tanggal:** 6 Oktober 2026  
**Acuan:** AGENTS.md v4.0 · Production Readiness Checklist · Alignment Map

---

## Prinsip Rencana

1. Yang paling krusial dikerjakan dulu.
2. Setiap fase harus **bisa diuji di versi installed**, bukan hanya di development.
3. Persona, PathJail, Action-First, dan Zero-Trust tidak boleh dikorbankan.
4. Setiap langkah Ruka harus menjadi batu bata Noctis yang sah.

---

## FASE 0 — Gerbang Produksi (Paling Krusial)
**Tujuan:** Memastikan Agentic Mode benar-benar hidup setelah Ruka di-install.

**Durasi fokus:** sampai lulus semua checklist di bawah.

### 0.1 Skills ikut ter-bundle
- [x] Folder `skills/` masuk ke artefak `ruka-brain.exe` / resources installer
- [x] Verifikasi isi skills setelah build (code_read, code_edit, run_terminal, git_*, repo_map, dll)

### 0.2 Path resolution di frozen mode
- [x] `get_skills_dir()` (atau setara) memakai `sys._MEIPASS` + fallback yang benar
- [x] Tidak hardcode path development

### 0.3 Wiring brain ↔ gateway (sudah ada di launcher — verifikasi ulang)
- [x] `brain.skill_registry` terisi
- [x] `brain.skills_runtime` terisi
- [x] `brain.confirmations` terisi
- [x] Log jelas jika Gateway gagal init

### 0.4 Uji di versi installed (bukan dev)
Dari **Desktop UI** dan **CLI global (`ruka`)**:
- [x] “Baca package.json” → skill sungguhan, bukan `[SYSTEM_CALL]`
- [x] “Lihat isi folder ini” / `ls` → hasil nyata
- [x] Edit file sederhana → berhasil + persona tetap
- [x] Git status / diff → hasil nyata
- [x] Tidak meminta user menempelkan output terminal

### 0.5 Negative test
- [x] Tidak muncul teks palsu `[SYSTEM_CALL: ...]`
- [x] PathJail menolak path di luar batas
- [x] Aksi berbahaya meminta konfirmasi

**Kriteria lulus Fase 0:**  
Young Lord bisa memakai Ruka yang di-install untuk tugas coding dasar tanpa roleplay.

**Artefak:** centang di `RUKA_Production_Readiness_Checklist.md` + log uji singkat.

---

## FASE 1 — Agentic yang Tajam
**Tujuan:** Mendekati kekuatan coding Claude Code di tugas nyata.

### 1.1 Multi-step yang andal
- [x] Planner agentic menangani 3–7 langkah tanpa putus
- [x] LoopGuard + BudgetController aktif dan diuji
- [x] Gagal di tengah → pesan jelas bergaya Marquis + opsi lanjut

### 1.2 Test → Fix → Verify
- [x] Skill / alur: jalankan test → baca gagal → perbaiki → jalankan lagi
- [x] Minimal satu jalur (pytest atau npm test) yang stabil

### 1.3 Git workflow
- [x] `git_status`, `git_diff`, `git_log` stabil
- [x] `git_commit` dengan pesan wajar + konfirmasi jika perlu
- [x] Branch dasar (buat / pindah) jika memungkinkan tanpa risiko tinggi

### 1.4 Project understanding
- [x] `repo_map` memberi gambaran struktur yang berguna
- [x] Agentic bisa menjawab “arsitektur repo ini bagaimana?” dengan bukti dari skill

### 1.5 Konsistensi permukaan
- [x] Desktop dan CLI memakai jalur agentic yang sama
- [x] Hasil dan persona konsisten di keduanya

**Kriteria lulus Fase 1:**  
Tugas multi-file + test + git dasar bisa diselesaikan dengan aksi nyata dan persona utuh.

---

## FASE 2 — Integrasi Kernel Bun
**Tujuan:** Kernel Noctis tidak hanya ada di folder, tapi menjadi pusat kendali yang hidup.

### 2.1 Kontrak komunikasi
- [x] Dokumentasikan: Electron ↔ Bun Kernel ↔ Python Organs
- [x] Endpoint discovery selaras (`kernel-endpoint.json` vs `ipc-endpoint.json`)
- [x] Hindari dua otak yang tidak sinkron

### 2.2 Boot tunggal
- [x] BootOrchestrator (Bun) menjadi sumber kebenaran urutan nyala
- [x] Python organs / brain di-spawn atau di-supervise dengan jelas
- [x] Cold boot terukur (target mendekati spek Noctis, realistis dulu)

### 2.3 Supervisor & Governor aktif
- [x] Organ terdaftar di Bun `OrganSupervisor`
- [x] Heartbeat / liveness dari organs sampai ke kernel
- [x] ResourceGovernor punya batas yang diuji (minimal log + degradasi dasar)

### 2.4 EventBus bridge
- [x] Event dari Python Gateway dan Bun Kernel tidak bertabrakan
- [x] Namespace organ dihormati (single-writer discipline)

**Kriteria lulus Fase 2:**  
Satu perintah/start membangkitkan kernel + brain/organs dengan health yang bisa dibaca; tidak ada jalur “aneh” yang saling mengabaikan.

---

## FASE 3 — Memori & Tangan yang Lebih Dalam
**Tujuan:** Companion lebih ingat; Hands lebih berguna.

### 3.1 Memory Palace (benih)
- [x] Perluas memory menjadi sayap: relationship, project, preference (minimal)
- [x] Recall yang dipakai agentic & percakapan
- [x] Tidak merusak identity/doctrine yang ada

### 3.2 Shadow Hands
- [x] Konfirmasi merah + audit trail untuk aksi berisiko
- [x] Perluas aksi aman bertahap (tetap PathJail)
- [x] Integrasi dengan agentic (bukan tool terpisah yang dilupakan)

### 3.3 Conversation depth
- [x] Barge-in / interupsi dasar jika voice aktif
- [x] Konteks percakapan tidak hilang saat ganti mode agentic ↔ chitchat

**Kriteria lulus Fase 3:**  
Ruka mengingat preferensi/proyek dengan lebih jelas; aksi desktop/file tetap aman dan teraudit.

---

## FASE 4 — Organ Kehadiran (Selektif)
**Hanya setelah Fase 0–2 stabil.**

### 4.1 Presence ringan
- [x] Indikator hidup / tray / status yang terasa “hadir”
- [x] Belum wajib avatar 3D

### 4.2 Ear / Voice
- [x] Wake word atau jalur suara yang lebih andal (jika sudah ada benih)
- [x] TTS/ASR tidak merusak latensi percakapan inti

### 4.3 Eyes / Avatar / Forge
- [x] Ditunda sampai ada kebutuhan nyata dan fondasi kuat
- [x] Jika dikerjakan, harus opt-in dan tidak mengganggu anggaran inti

---

## Urutan Eksekusi (Ringkas)

```
FASE 0  Production gate (installed Agentic)
   ↓
FASE 1  Agentic tajam (multi-step, test-fix, git, konsistensi)
   ↓
FASE 2  Bun Kernel terintegrasi (boot, supervisor, bus)
   ↓
FASE 3  Memory + Hands + conversation depth
   ↓
FASE 4  Presence / organ kehadiran (selektif)
```

Jangan loncat ke Fase 4 sebelum Fase 0 lulus.

---

## Definition of Done per Fase

| Fase | Selesai jika |
|------|----------------|
| 0 | Install → coding dasar jalan tanpa roleplay |
| 1 | Multi-step + test/fix + git dasar andal di Desktop & CLI |
| 2 | Kernel Bun + organs/brain satu jalur boot & health |
| 3 | Memory lebih kaya + Hands lebih aman/berguna |
| 4 | Kehadiran terasa tanpa merusak stabilitas |

---

## Yang Tidak Masuk Rencana Ini (Sengaja)

- ElysiaJS (opsional nanti, jika butuh HTTP control plane)
- Avatar VRM penuh
- Forge / simulasi ilmiah
- Cloud parallel sessions
- Mengganti seluruh stack Python sebelum bridge stabil

---

## Cara Memakai Rencana Ini

1. Mulai dari **Fase 0** — jangan ke mana-mana sebelum gerbang produksi hijau.
2. Setiap item centang hanya setelah **diuji di lingkungan yang relevan** (installed untuk 0–1).
3. PR / commit yang menyentuh Skills, Gateway, Agentic, path, atau Kernel wajib menyinggung fase mana yang dilayani.
4. Jika ada konflik prioritas: **Fase lebih awal menang**.

---

*— Rencana ini adalah urutan kerja resmi dari yang paling krusial, selaras AGENTS.md v4.0 dan PROJECT NOCTIS.*
