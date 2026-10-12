# RUKA / NOCTIS — Roadmap “Bisa Dipakai” → Spirit JARVIS
**Desktop + CLI · Fitur nyata · Bukan ilusi folder**

**Versi:** 1.0  
**Tanggal:** 12 Oktober 2026  
**Wajib dibaca bersama:** AGENTS.md · AGENT_STRICT_PROTOCOL.md · ANTIGRAVITY_HARD_RULES.md · RUKA_JARVIS_Path_Design.md

---

## 0. Realita dulu (anti-bohong)

**“100% mirip JARVIS”** di film tidak bisa dijanjikan sebagai DoD engineering.  
Yang bisa dikejar secara serius:

> **Ruka terasa seperti asisten desktop lokal yang andal:**  
> dipanggil lewat UI atau CLI, bertindak nyata, ingat konteks, cepat di tugas ringan, persona utuh, safety ketat — spirit JARVIS di PC (tanpa smart home).

Target produk yang jujur: **nyaman dipakai setiap hari** di Desktop **dan** CLI, dengan rantai fitur **end-to-end**, bukan shell Vue / class kosong.

Status default setiap tiket agent: **BELUM SIAP DIGUNAKAN** sampai DoD tiket + bukti uji (idealnya installed) lulus.

---

## 1. Definisi “bisa digunakan dengan nyaman”

Sebuah fitur Noctis/Ruka **baru** boleh disebut usable jika **semua** ini benar:

| # | Syarat |
|---|--------|
| 1 | Satu cara jelas memicu dari **Desktop** dan/atau **CLI** (sesuai sifat fitur) |
| 2 | Rantai **input → organ/brain → output nyata** (disk, UI berubah, suara, status) terbukti |
| 3 | Bukan stub / fake reply / status “hijau” palsu |
| 4 | Error gagal dengan pesan jujur bergaya Marquis, bukan hang |
| 5 | Tidak merusak PathJail / konfirmasi destruktif |
| 6 | Latency terasa masuk akal untuk kelas fiturnya (ringan ≠ refactor besar) |
| 7 | Diuji di lingkungan yang relevan (dev **dan** installed bila menyentuh bundle) |
| 8 | Identitas: Ruka / Marquis / Noctis — **bukan** Jarvis di UI |

Tanpa ini: **shell**, bukan fitur.

---

## 2. Paritas Desktop ↔ CLI

| Kapabilitas | CLI (`ruka` / brain host) | Desktop (Vue + Electron) |
|-------------|---------------------------|---------------------------|
| Chat / titah teks | ✅ jalur utama | ChatView → IPC → brain yang **sama** |
| Agentic coding di folder | ✅ SkillsRuntime | CodeView / chat coding → **runtime yang sama**, bukan logika duplikat |
| Konfirmasi destruktif | prompt CLI | dialog / kartu UI yang memanggil kontrak konfirmasi yang sama |
| Status health | perintah/status teks | KernelView / OrgansView dari data **nyata**, bukan konstanta |
| Memory recall | lewat percakapan / perintah | MemoryView baca store yang **sama** |
| Voice (nanti) | opsional | push-to-talk / wake — backend indra yang sama |

**Aturan keras:**  
Satu otak (Python brain + skills + gateway).  
Desktop dan CLI hanya **permukaan**.  
Dilarang implementasi “khusus Vue” yang tidak ada di brain untuk kapabilitas inti.

---

## 3. Pilar pengalaman “asisten ala JARVIS” (lokal)

Urutan prioritas pengalaman user:

1. **Percaya** — perintah dikerjakan nyata; tidak berbohong  
2. **Cepat** — tugas ringan tidak terasa berat  
3. **Satu di mana-mana** — CLI dan Desktop perilaku selaras  
4. **Ingat** — preferensi & proyek muncul lagi  
5. **Aman** — tidak menghapus/menulis liar tanpa konfirmasi  
6. **Hadir** — mudah dipanggil; tray/status jujur  
7. **Bersuara / terlihat** — voice & avatar **setelah** 1–5 stabil  

Avatar cantik tanpa 1–3 = demo, bukan asisten.

---

## 4. Roadmap fase (wajib berurutan)

### FASE U0 — Kejujuran permukaan (1 fondasi)
**Tujuan:** User dan agent tidak ditipu UI.

| ID | Kerja | DoD ringkas |
|----|--------|-------------|
| U0.1 | Audit ChatView / kirim pesan: stub vs brain sungguhan | Dokumen rantai + patch agar path utama ke brain |
| U0.2 | Audit CodeView: perintah coding → skills/brain yang sama dengan CLI | Satu perintah uji file di disk berubah dari Desktop |
| U0.3 | KernelView / OrgansView: status dari connector nyata; offline = offline | Matikan brain/kernel → UI berubah |
| U0.4 | Hapus/labeli eksplisit semua fallback “Heh… titah diterima…” palsu di production path | Tidak ada reply kemenangan tanpa runtime |

**Keluar fase:** Young Lord tahu mana yang hidup dan mana shell.

---

### FASE U1 — Asisten coding yang nyaman (Desktop + CLI)
**Tujuan:** Inti “JARVIS kerja” — kerjakan tugas di folder tanpa drama.

| ID | Kerja | DoD ringkas |
|----|--------|-------------|
| U1.1 | Fast path agentic + `model_tier=fast` konsisten + log model | Latency tugas ringan turun / terukur |
| U1.2 | Multi-step: baca → ubah → ringkas tanpa putus total | 1 skenario uji tertulis lulus CLI **dan** Desktop |
| U1.3 | Git dasar andal (status, diff, commit + konfirmasi) | Sama di CLI & Desktop |
| U1.4 | Production: skills + path frozen / installer | Ulangi U1.2 di **installed** |
| U1.5 | Pesan error & progress jelas (Marquis, tidak roleplay tool) | Tidak ada `[SYSTEM_CALL]` |

**Keluar fase:** Ruka terasa asisten coding harian, bukan demo agentic.

---

### FASE U2 — Satu sistem hidup (Kernel + boot + health)
**Tujuan:** Noctis terasa OS companion, bukan dua proses acak.

| ID | Kerja | DoD ringkas |
|----|--------|-------------|
| U2.1 | Boot path tunggal: Electron → kernel dan/atau brain terurut | Satu start; dokumentasi urutan |
| U2.2 | Health end-to-end: supervisor ↔ UI | Offline/degraded terlihat di Desktop; CLI status selaras |
| U2.3 | Event/jembatan tanpa dual kebenaran bus | Kontrak tertulis + uji publish sederhana |
| U2.4 | Resource/budget tidak membuat hang diam | Gagal → pesan jujur |

**Keluar fase:** “Noctis” punya denyut yang bisa dipercaya.

---

### FASE U3 — Ingatan & tangan steward
**Tujuan:** Asisten yang ingat dan bertindak lebih luas dengan aman.

| ID | Kerja | DoD ringkas |
|----|--------|-------------|
| U3.1 | Memory: minimal preference + project recall setelah restart | Uji: simpan → restart → recall CLI & Desktop |
| U3.2 | Hands: konfirmasi merah + audit untuk aksi berisiko | Uji destruktif tidak jalan tanpa setuju |
| U3.3 | Konteks tidak hilang saat ganti Chat ↔ Code | Satu sesi, dua view, konteks lanjut |
| U3.4 | Paritas perintah “ingat / lupakan / status kerja” CLI ↔ UI | Perilaku sama |

**Keluar fase:** Terasa “mengenal” Young Lord di batas yang diuji.

---

### FASE U4 — Kehadiran & suara (spirit JARVIS)
**Hanya setelah U1–U2 stabil.**

| ID | Kerja | DoD ringkas |
|----|--------|-------------|
| U4.1 | Tray/presence jujur + panggil cepat ke chat | Tidak menipu status |
| U4.2 | Voice in → teks → brain → (opsional) TTS; latensi terukur | Satu loop uji nyaman |
| U4.3 | Wake/VAD (C++/native) bila siap — fail-closed | Gagal → teks tetap bisa |
| U4.4 | Avatar: **hanya** jika engine → renderer terbukti; jika tidak, tetap sebut shell | Ekspresi/viseme terlihat ATAU eksplisit “belum” |

**Keluar fase:** Bisa didekati seperti asisten hadir, masih lokal, tanpa smart home.

---

### FASE U5 — Poles kenyamanan (bukan fitur baru besar)

- Shortcut Desktop, command palette, CLI help konsisten  
- Logging latency opsional di UI dev  
- Dokumen user singkat: “cara pakai Ruka sehari-hari” (CLI + Desktop)  
- Tidak menambah organ spekulatif

---

## 5. Urutan yang dilarang

Jangan:

1. Mengasah avatar/Three.js sebelum Chat/Code → brain terbukti  
2. Menambah organ folder baru sebelum U1 usable  
3. Menyatakan “100% JARVIS” di UI atau laporan agent  
4. Implementasi terpisah CLI vs Desktop untuk logic inti  
5. Menutup fase karena “kompilasi sukses”

---

## 6. Cara memberi tiket ke Antigravity (wajib)

Setiap tiket:

```text
WAJIB: AGENTS.md + AGENT_STRICT_PROTOCOL.md + ANTIGRAVITY_HARD_RULES.md
+ RUKA_NOCTIS_USABLE_JARVIS_ROADMAP.md

Tugas (HANYA ini):
<satu ID dari roadmap, mis. U1.1>

DoD:
1. ...
2. ...
3. Bukti uji CLI dan/atau Desktop sesuai sifat tugas
4. Laporan format §3 Hard Rules
5. Status: BELUM SIAP DIGUNAKAN sampai DoD lulus

Dilarang: selesai, siap digunakan, JARVIS, Noctis complete, perluas scope.
```

Kerjakan **satu ID** per sesi. Jangan “implementasi semua Noctis”.

---

## 7. Backlog urutan eksekusi (untuk Anda / agent)

```
U0.1 → U0.2 → U0.3 → U0.4
  → U1.1 → U1.2 → U1.3 → U1.4 → U1.5
    → U2.1 → U2.2 → U2.3 → U2.4
      → U3.1 → U3.2 → U3.3 → U3.4
        → U4.1 → U4.2 → U4.3 → U4.4
          → U5
```

Ini jalur terpendek agar Ruka **terasa asisten**, bukan museum organ.

---

## 8. Ukuran “mendekati JARVIS lokal” (bukan 100% film)

| Tingkat | Arti |
|---------|------|
| **Nyaman harian** | U1 + U0 lulus — coding & chat andal di CLI & Desktop |
| **Companion sistem** | + U2 + U3 — health, ingat, tangan aman |
| **Spirit JARVIS di PC** | + U4 — hadir, suara, (opsional) avatar **terbukti** |
| **100% film** | Di luar scope; jangan jadi DoD |

Janji yang boleh dipakai ke diri sendiri:

> “Ruka nyaman sebagai asisten lokal di Desktop dan CLI, dengan spirit JARVIS.”  

Janji yang dilarang ke agent dan UI:

> “100% JARVIS / sudah selesai semua Noctis.”

---

## 9. Penutup

Fitur Noctis yang baik = **bisa dipakai dengan nyaman**, bukan **terlihat di tree**.

Urutan kemenangan:

1. Jujur soal shell vs hidup (U0)  
2. Coding + chat tajam di **CLI dan Desktop** (U1)  
3. Satu napas kernel/health (U2)  
4. Ingat & tangan aman (U3)  
5. Hadir & suara (U4)  

Dengan disiplin itu, Ruka mendekati asisten ala JARVIS di laptop — tanpa bohong, tanpa smart home, tanpa avatar palsu yang pura-pura hidup.

---

*— RUKA_NOCTIS_USABLE_JARVIS_ROADMAP v1.0*  
*Marquis of Trendamis Development Council*
