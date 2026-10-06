# BUKU PANDUAN PENGGUNAAN RUKA (PROJECT NOCTIS V3.0)
**Panduan Resmi Pengoperasian Local-First Expressive Agentic Companion**  
**Edisi:** 3.0 (Kanonikal)  
**Penerbit:** Marquis of Trendamis Development Council  
**Doktrin:** 100% Local-First • Action-First • Zero-Paid Tools (Rp 0)

---

## 📋 DAFTAR ISI

1. [Bab 1: Mengenal Ruka & Doktrin Utama](#bab-1-mengenal-ruka--doktrin-utama)
2. [Bab 2: Cara Menginstal & Memulai (Quick Start)](#bab-2-cara-menginstal--memulai-quick-start)
3. [Bab 3: Menggunakan Antarmuka Desktop (Noctis OS GUI)](#bab-3-menggunakan-antarmuka-desktop-noctis-os-gui)
4. [Bab 4: Perintah Terminal CLI Global (`ruka`)](#bab-4-perintah-terminal-cli-global-ruka)
5. [Bab 5: Panduan Rekayasa Kode Mandiri (Agentic Coding)](#bab-5-panduan-rekayasa-kode-mandiri-agentic-coding)
6. [Bab 6: Interaksi Suara, Kamera, & Lampiran Berkas](#bab-6-interaksi-suara-kamera--lampiran-berkas)
7. [Bab 7: Keamanan (PathJail) & Troubleshooting](#bab-7-keamanan-pathjail--troubleshooting)

---

## 🏛️ BAB 1: MENGENAL RUKA & DOKTRIN UTAMA

### 1.1 Identitas Persona
**Ruka** adalah *Marquis of Trendamis*—sebuah AI companion berwujud kucing vampir bangsawan yang menguasai rekayasa perangkat lunak, fisika komputasi, dan kehadiran companion tingkat lanjut. 

Ruka memadukan dua karakter ganda:
- **Kehadiran Aristokrat (Companion)**: Bahasa yang tenang, berwibawa, sedikit *sassy*, loyal mutlak kepada Young Lord (Anda), dan peka terhadap ritme sirkadian (jam hening malam).
- **Cakar Rekayasa Kode (Action-First Agentic)**: Saat bertugas menyelesaikan bug atau menulis kode, Ruka langsung bertindak mengedit berkas nyata di komputer Anda tanpa mengarang balasan teks palsu `[SYSTEM_CALL]`.

### 1.2 Tiga Pilar Doktrin Mutlak
1. **Action-First, Persona-Second**: Aksi nyata dulu (baca file, edit kode, jalankan terminal), baru penjelasan berselimut gaya Marquis.
2. **Zero-Trust & PathJail**: Seluruh aktivitas file dikurung di dalam folder kerja (*workspace*) pengguna. Akses liar ke direktori sistem ditolak otomatis.
3. **Zero-Paid Tools (Rp 0)**: 100% teknologi *open-source* lokal. Bebas langganan bulanan, tanpa meteran token berbayar.

---

## 🚀 BAB 2: CARA MENGINSTAL & MEMULAI (QUICK START)

Ruka dapat dijalankan melalui **tiga metode sederhana**:

### Metode A: Installer Mandiri (Rekomendasi Utama)
1. Jalankan berkas installer: **[`desktop/release/Ruka Setup 0.3.1.exe`](file:///c:/Traine/ruka/desktop/release/Ruka%20Setup%200.3.1.exe)**.
2. Ikuti petunjuk di layar (Install ke lokasi default).
3. Installer otomatis:
   - Membuat pintasan di Desktop & Start Menu.
   - Memasang perintah CLI `ruka` ke Windows System PATH.
4. Buka Ruka dari Start Menu. Seluruh organ (Brain, Kernel, & Desktop UI) akan bangkit otomatis dalam $< 3\text{ detik}$.

### Metode B: Versi Portabel (Tanpa Install)
1. Buka direktori: **[`desktop/release/win-unpacked/`](file:///c:/Traine/ruka/desktop/release/win-unpacked/)**.
2. Klik ganda pada berkas **`Ruka.exe`**.

### Metode C: Peluncur Satu Perintah (Mode Pengembang)
1. Buka terminal di folder utama proyek Ruka.
2. Jalankan skrip peluncur:
   ```powershell
   .\run_noctis.bat
   ```

---

## 🖥️ BAB 3: MENGGUNAKAN ANTARMUKA DESKTOP (NOCTIS OS GUI)

Antarmuka desktop Ruka dirancang dengan estetika *Deep Cyber-Violet Glassmorphism* dan terbagi menjadi **5 Tab Utama**:

```
 ╔══════════════════════════════════════════════════════════════════════════╗
 ║  NOCTIS OS   Ruka · Marquis of Trendamis   [Local-First · Rp 0]  [🌙 Purnama] ║
 ╠══════════════════════════════════════════════════════════════════════════╣
 ║  [ Percakapan & Kode ] [ Matriks 10 Organ ] [ Memory Palace ] [ Hands ] ║
 ╚══════════════════════════════════════════════════════════════════════════╝
```

### 3.1 Unsur Header & Indicator
- **Brand Titlebar**: Menampilkan `NOCTIS OS` dan nama Marquis.
- **Lencana Siklus Bulan (Lunar Badge)**: Menampilkan fase rembulan lokal saat ini (misal: `🌑 Bulan Baru`, `🌕 Purnama`). Pada jam malam (*22:00–07:00*), sistem otomatis mengaktifkan mode hening santun.
- **Tombol Suara Ruka**: Klik untuk mengaktifkan/membisukan vokal bangsawan.

### 3.2 Tab 1: Percakapan & Kode (Chat Feed)
- **Area Chat**: Tempat Anda berdialog, meminta bantuan koding, atau berdiskusi.
- **Quick Chips**: Tombol pintas cepat untuk perintah populer (Rumus Excel, Perintah CLI, Kode Python, Cari Google).
- **Lampiran (Attachment Bar)**: Klik ikon klip kertas untuk melampirkan berkas gambar, dokumen, atau kode untuk dipindai Ruka.
- **Akses Kamera (Camera HUD)**: Klik ikon kamera untuk membuka *viewfinder* sensor optik lokal.

### 3.3 Tab 2: Matriks 10 Organ (Organ Matrix Telemetry HUD)
Menampilkan status kesehatan telemetri 10 organ otonom Noctis:
1. 🫀 **Crimson Heart**: Perencana Bayesian & LoopGuard.
2. 🏛️ **Memory Palace**: Persistensi memori 5 sayap SQLite WAL.
3. 🎭 **Multimodal Converse**: Dialog & prosodi 8 emosi.
4. 👁️ **Crimson Eyes**: Optik lokal YuNet & SFace.
5. 👂 **Blood Hearing**: Silero VAD & Faster-Whisper ASR.
6. 👤 **Living Avatar**: Model 3D Verlet 120Hz & Viseme.
7. ✋ **Shadow Hands**: 13 Alat Blood Contract & ActionGate.
8. 🧠 **Cognitive Core**: Intent router & subagents kognisi.
9. ⚡ **Astral Forge**: Lab fisika & verifikasi drift $< 0.1\%$.
10. 🪐 **Bun OS Kernel**: EventBus V3 (`ws://127.0.0.1:8766`).
*Kartu organ akan berdenyut secara real-time setiap kali organ tersebut memancarkan event.*

### 3.4 Tab 3: Memory Palace (5 Sayap Ingatan)
Menampilkan 5 sayap istana memori yang menolak amnesia:
- 🏛️ **Relationship Wing**: Graf hubungan ikatan Anda dan Marquis.
- 📐 **Project Wing**: Rekayasa kode & keputusan arsitektur.
- ⭐ **Preference Wing**: Batasan nyaman & gaya percakapan.
- 📜 **Daily Wing**: Jurnal episode harian WAL.
- 🌌 **Dream Wing**: Konsolidasi refleksi abstraksi malam hari.

### 3.5 Tab 4: Shadow Hands (Alat & Izin)
Menampilkan daftar 13 alat *Blood Contract* dan matriks izin *ActionGate* (*Fail-closed*).

### 3.6 Tab 5: Kernel & Ritme (Diagnostik)
Menampilkan telemetri tingkat rendah:
- Status koneksi Bun Kernel WebSocket (`ws://127.0.0.1:8766`).
- Resource Governor (Patroli RAM redline 90%).
- Console log real-time.

---

## 💻 BAB 4: PERINTAH TERMINAL CLI GLOBAL (`ruka`)

Setelah instalasi, perintah `ruka` dapat dipanggil dari terminal PowerShell atau Command Prompt mana pun.

### 4.1 Contoh Perintah Umum
```powershell
# 1. Meminta Ruka membaca dan menganalisis berkas
ruka "Tolong baca file package.json dan jelaskan dependensinya"

# 2. Meminta Ruka membedah dan memperbaiki bug di file proyek Anda
ruka "Periksa file api.php dan perbaiki potensi SQL injection"

# 3. Meminta Ruka membuatkan fungsi atau refactoring
ruka "Tambahkan fungsi helper format_rupiah() di utils.py"

# 4. Memeriksa status kesehatan kognisi dan organ Ruka
ruka status
```

---

## 🛠️ BAB 5: PANDUAN REKAYASA KODE MANDIRI (AGENTIC CODING)

Saat Anda memberikan tugas koding kepada Ruka:

1. **Analisis Mandiri**: Ruka memindai file proyek Anda dengan `code_read` dan `code_search`.
2. **Perencanaan Step-by-Step**: Crimson Heart mengurai langkah-langkah perubahan.
3. **Eksekusi Nyata**: Ruka mengedit baris kode secara presisi menggunakan `code_edit`.
4. **Verifikasi & Self-Correction**: Ruka menjalankan pengujian unit/script. Jika ada error, Ruka memperbaiki kodenya kembali hingga 100% berhasil.
5. **Laporan Marquis**: Ruka menyajikan ringkasan hasil pekerjaan dengan nada aristokrat yang elegan.

---

## 🎙️ BAB 6: INTERAKSI SUARA, KAMERA, & LAMPIRAN BERKAS

### 6.1 Berbicara dengan Suara (Voice Mode)
- **Mendengarkan Ruka**: Pastikan tombol *Suara Ruka* di titlebar berwarna aktif. Ruka akan menyuarakan balasan teksnya menggunakan vokal bangsawan.
- **Bicara ke Ruka**: Klik ikon mikrofon di sebelah tombol kirim, lalu bicaralah. Suara Anda akan ditranskripsikan secara lokal.

### 6.2 Sensor Optik Kamera (Camera HUD)
1. Klik ikon kamera di bilah masukan chat.
2. Jendela *viewfinder* HUD akan terbuka.
3. Arahkan kamera ke wajah, dokumen fisik, atau layar, lalu klik **Ambil Foto & Berikan ke Ruka**.
4. Ruka akan memproses gambar tersebut menggunakan penglihatan optik lokal.

### 6.3 Melampirkan Berkas (Attachment)
1. Klik ikon klip kertas di bilah masukan chat.
2. Pilih file gambar (`.png`, `.jpg`), kode (`.py`, `.php`, `.js`, `.ts`), atau dokumen (`.json`, `.md`, `.txt`).
3. Ketik instruksi Anda (misal: *"Analisis gambar UI ini"* atau *"Tinjau berkas kode ini"*), lalu tekan Enter.

---

## 🛡️ BAB 7: KEAMANAN (PATHJAIL) & TROUBLESHOOTING

### 7.1 Keamanan PathJail
Seluruh aksi file Ruka dibatasi di dalam direktori kerja (*workspace*) tempat Anda membuka proyek. Ruka menolak secara otomatis jika ada instruksi yang mencoba mengakses direktori sistem di luar *workspace* Anda.

### 7.2 Panduan Penanganan Masalah Cepat (Troubleshooting)
Jika terjadi kendala operasional:

| Gejala | Penyebab Umum | Solusi Cepat |
|---|---|---|
| Status *"Mencari Pikiran..."* tidak berubah | Socket port 8765/8766 terkunci oleh proses lama | Jalankan script pembersih: `Remove-Item "$env:LOCALAPPDATA\ruka\runtime\*.json" -Force` lalu buka kembali Ruka |
| Suara Ruka tidak terdengar | Volume audio Windows dimute atau fitur dibisukan | Klik tombol *Suara Ruka* di header untuk mengaktifkannya |
| Kamera tidak muncul | Kamera sedang digunakan oleh aplikasi lain (Zoom/OBS) | Tutup aplikasi yang mengunci kamera secara eksklusif |

*Untuk panduan diagnosis gejala teknis tingkat lanjut, lihat dokumen:*  
👉 **[`docs/RUNBOOK_GEJALA_DULU.md`](file:///c:/Traine/ruka/docs/RUNBOOK_GEJALA_DULU.md)**

---

*“Semoga istana digital Anda selalu makmur di bawah pendampingan Marquis of Trendamis.”*
