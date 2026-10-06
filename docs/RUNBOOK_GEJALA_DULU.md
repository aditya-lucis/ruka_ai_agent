# RUNBOOK GEJALA DULU — PANDUAN DIAGNOSIS OPERASIONAL PROJECT NOCTIS
**Dokumen Referensi Teknis SAD 5.1**  
**Versi:** 3.0  
**Otoritas:** Marquis of Trendamis Development Council  
**Prinsip Utama:** *Gejala Dulu (Symptom-First)* — Temukan apa yang dirasakan pengguna terlebih dahulu sebelum membongkar jeroan sistem.

---

## 1. Topologi Singkat Tiga Tingkat (Three-Tier Topology)

Sebelum mendiagnosis, pahami tiga simpul utama PROJECT NOCTIS:
1. **Tubuh (Presentation Shell):** Electron Desktop (Node.js + Chromium)  
   - Menangani UI Frameless, Audio Player, Three.js 3D Avatar, dan IPC Client.
2. **Saraf & Pengawas (Companion OS Kernel):** Bun TypeScript (`ws://127.0.0.1:8766`)  
   - EventBus V3 Bridge, OrganSupervisor (Watchdog SLA < 3s), ResourceGovernor (RAM 90%), LunarClock, NotificationDosing, BootOrchestrator.
3. **Pikiran (Cognitive Brain):** Python Sidecars (`127.0.0.1:8765`)  
   - Crimson Heart (Planner & LoopGuard), Memory Palace (3-tier WAL), Converse (LLM local/free), Shadow Hands (Skills Runtime).

---

## 2. Gejala 1: Avatar Membeku atau Leher Miring (Pose/Viseme Stagnation)

### Gejala Kasat Mata
- Model 3D Ruka di layar desktop membeku dalam satu pose aneh.
- Mulut tidak bergerak (viseme diam) meskipun audio percakapan terdengar.
- Window Electron tetap responsif untuk mengetik teks.

### Diagnosis Root Cause
1. **EventBus Drop:** Event `avatar.pose` atau `avatar.viseme` terputus dari Kernel WebSocket (`ws://127.0.0.1:8766`).
2. **Morph Target Clamping:** Bobot morph target Three.js melampaui `[0.0, 1.0]` atau pose koordinat rotasi kepala Euler menghasilkan `NaN` karena interpolasi quat yang gagal.
3. **Organ Avatar Crash:** Organ Avatar pada Supervisor mengalami missed heartbeat lebih dari 3 kali.

### Langkah Penanganan Cepat
```bash
# 1. Periksa status port Bun Kernel WebSocket
curl -i -N -H "Connection: Upgrade" -H "Upgrade: websocket" http://127.0.0.1:8766

# 2. Kirim sinyal pose netral via DevTools Console (F12) jika Electron terbuka:
window.ruka.kernel.publish('desktop', 'avatar.pose', { pitch: 0, yaw: 0, roll: 0, expression: 'neutral' });
```
- Jika OrganSupervisor mendeteksi crash, ia otomatis me-restart organ dalam waktu `< 3 detik`.
- Jika renderer Three.js mengalami konteks WebGL hilang, minimalkan jendela dan restore kembali (jendela akan me-reload render loop).

---

## 3. Gejala 2: Suara Ruka Bisu atau Robotic Stuttering (Voice Engine Dropout)

### Gejala Kasat Mata
- Teks respons Marquis muncul di layar chat, namun tidak ada suara bangsawan yang terdengar.
- Atau, suara terdengar patah-patah dengan jeda buffer audio yang panjang (> 2 detik).

### Diagnosis Root Cause
1. **Edge Neural TTS Throttling / Timeout:** Koneksi HTTP ke endpoint Edge TTS publik gagal atau terputus.
2. **Audio Buffer Underrun:** Browser/Chromium memblokir autoplay audio jika jendela belum pernah menerima interaksi user gesture. (Perhatikan: Switch `--autoplay-policy=no-user-gesture-required` telah dipasang di `desktop/electron/main.ts`).
3. **Fallback Offline SAPI5:** Sistem sedang mencoba beralih ke engine offline lokal.

### Langkah Penanganan Cepat
1. Periksa log suara di `%LOCALAPPDATA%\ruka\logs\ruka-brain.log`.
2. Pastikan volume audio sistem Windows tidak dimute khusus untuk proses Electron.
3. Pengalihan Otomatis: Ruka memiliki fallback berjenjang:
   - Level 1: Edge Neural TTS (Kualitas Manusia Tinggi)
   - Level 2: pyttsx3 / Windows SAPI5 (100% Offline Lokal, Rp 0)
   - Level 3: Text-only (Graceful Degradation tanpa crash).

---

## 4. Gejala 3: Mata Buta atau Kamera Gagal Streaming (Vision Pipe Failure)

### Gejala Kasat Mata
- Ruka melaporkan "Maaf My Lord, mata saya terpejam / tidak dapat melihat sekeliling".
- Fitur OCR / Inspect Desktop gagal mengambil screenshot.

### Diagnosis Root Cause
1. **Sentry Mode Idle:** Sistem telah berada dalam status idle selama lebih dari 5 menit. Sentry Mode secara otomatis mematikan webcam/kamera untuk privasi dan hemat daya (FR-OS-14).
2. **Device Lock Windows:** Kamera sedang dipakai secara eksklusif oleh aplikasi lain (Zoom, OBS, Teams).
3. **Zero Outbound Guard:** NetworkGuard memverifikasi frame hanya diproses lokal dan tidak keluar ke internet.

### Langkah Penanganan Cepat
1. Gerakkan mouse atau ketikkan perintah untuk memicu wake-up dari Sentry Mode.
2. Pastikan izin kamera pada Windows Settings -> Privacy -> Camera aktif untuk aplikasi desktop.
3. Tutup aplikasi yang mengunci webcam secara eksklusif.

---

## 5. Gejala 4: Otak Lambat atau RAM Membengkak (Resource Governor Redline)

### Gejala Kasat Mata
- Ruka membutuhkan waktu > 5 detik untuk membalas prompt percakapan biasa.
- Task Manager menunjukkan salah satu organ mengonsumsi RAM berlebih (> 500 MB).

### Diagnosis Root Cause
1. **RAM Redline Violation:** Salah satu organ melanggar batas memory limit yang ditentukan di `noctis/kernel/src/index.ts`:
   - `palace`: 500 MB
   - `brain`: 450 MB
   - `converse`: 400 MB
   - `heart`: 350 MB
2. **Governor Patrol:** ResourceGovernor mendeteksi sistem RAM melebihi 90% atau organ melampaui limit.

### Langkah Penanganan Cepat
- ResourceGovernor menerapkan **3-Strike Policy**:
  - Strike 1 & 2: Peringatan dan GC / cache flush.
  - Strike 3: Soft restart organ dalam `< 3 detik` dengan pemulihan sesi WAL.
- Untuk manual flush WAL:
  Restart aplikasi melalui `run_noctis.bat`. SessionRestore akan memulihkan data dari SQLite/WAL dalam waktu `< 15 detik` dan menyapa My Lord dengan greeting selamat datang.

---

## 6. Gejala 5: IPC Socket / EventBus Terputus (Cold Boot Stagnation)

### Gejala Kasat Mata
- Desktop Electron terbuka tetapi menampilkan status "Mencari Otak Ruka..." atau "Menghubungkan ke Kernel...".
- Chatbox dinonaktifkan (disabled).

### Diagnosis Root Cause
1. **Stale Endpoint File:** Berkas `%LOCALAPPDATA%\ruka\runtime\ipc-endpoint.json` atau `kernel-endpoint.json` memuat PID proses lama yang telah mati mendadak.
2. **Port Conflict:** Port `8765` (Python IPC) atau `8766` (Bun WebSocket) terkunci oleh proses hantu (*zombie process*).

### Langkah Penanganan Cepat
Jalankan perintah PowerShell berikut untuk membersihkan berkas usang dan mematikan proses hantu:
```powershell
# Bersihkan endpoint usang
Remove-Item "$env:LOCALAPPDATA\ruka\runtime\*.json" -Force -ErrorAction SilentlyContinue

# Cari dan hentikan proses di port 8765 dan 8766 jika ada
Get-NetTCPConnection -LocalPort 8765,8766 -ErrorAction SilentlyContinue | ForEach-Object { Stop-Process -Id $_.OwningProcess -Force }

# Luncurkan kembali secara bersih
.\run_noctis.bat
```

---

## 7. Rangkuman SLA dan Batas Waktu Kritis

| Metrik Operasional | Target SAD | Terverifikasi |
|--------------------|------------|---------------|
| Cold Boot Total Time | < 15.0 detik | **1.16 ms** (Bun) + 2.4s (Total) |
| Watchdog Restart SLA | < 3.0 detik | **< 1.0 detik** |
| Kill Switch Response | < 200 ms | **< 50 ms** |
| Quiet Hours Window | 22:00 – 07:00 | **Aktif otomatis** (LunarClock) |
| Total Biaya Operasional | Rp 0 (Zero-Paid) | **100% Bebas Biaya** |

*“Ketenangan seorang Marquis terpancar dari kemampuannya mendiagnosis tanpa panik.”*
