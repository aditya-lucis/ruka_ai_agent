---
name: code_edit
version: 1.2.0
description: |
  Melakukan edit file secara presisi menggunakan mekanisme search-and-replace yang aman.
  Skill ini dirancang untuk perubahan kode yang terarah, refactor kecil hingga menengah,
  dan perbaikan bug yang sudah diketahui lokasinya.
author: Ruka Core Team
license: MIT
tags:
  - coding
  - filesystem
  - edit
  - refactor
risk_level: medium
requires_confirmation: false
permissions:
  - filesystem:read
  - filesystem:write
entry_point: main.py
timeout_seconds: 45
max_file_size_kb: 1024
compatible_ruka_version: ">=0.3.0"
---

# Code Edit Skill

## Deskripsi Lengkap

Skill `code_edit` memungkinkan Ruka melakukan perubahan pada file teks yang sudah ada dengan cara yang aman dan dapat diaudit.  
Ia menggunakan pendekatan **search-and-replace** (bukan rewrite penuh) agar risiko kerusakan kode lebih rendah.

Skill ini merupakan salah satu fondasi Coding Agent Ruka dan wajib melewati PathJail.

## Kapan Skill Ini Digunakan

**Gunakan** ketika:
- Young Lord meminta perubahan spesifik pada fungsi, class, atau blok kode tertentu
- Melakukan rename variabel / fungsi secara lokal
- Memperbaiki bug yang sudah diketahui lokasi dan pola kodenya
- Menambahkan sedikit logika di dalam fungsi yang sudah ada

**Jangan gunakan** ketika:
- Membuat file baru dari nol → gunakan skill `code_write`
- Perubahan sangat besar dan menyentuh banyak bagian → pertimbangkan plan dulu atau gunakan kombinasi skill
- File berada di luar workspace yang diizinkan

## Cara Kerja (Internal)

1. Gateway menerima permintaan pemanggilan skill.
2. PathJail memvalidasi path target.
3. File dibaca (utf-8, fallback latin-1).
4. Sistem menghitung jumlah kemunculan `old_string`.
5. Jika `replace_all = false` dan ditemukan lebih dari 1 kemunculan → gagal dengan pesan jelas.
6. Penggantian dilakukan.
7. File ditulis kembali.
8. Hasil dinormalisasi dan dikembalikan ke Cognitive Core.
9. Event `skill.executed` dipancarkan.

## Parameter

| Nama          | Tipe    | Wajib | Default | Keterangan                                      |
|---------------|---------|-------|---------|-------------------------------------------------|
| path          | string  | Ya    | -       | Path file relatif terhadap workspace            |
| old_string    | string  | Ya    | -       | Teks yang ingin diganti (disarankan unik)       |
| new_string    | string  | Ya    | -       | Teks pengganti                                  |
| replace_all   | boolean | Tidak | false   | Jika true, ganti semua kemunculan               |

## Aturan Keamanan (Wajib Dipatuhi)

- Semua path wajib melalui PathJail. Tidak ada pengecualian.
- Dilarang mengedit file di luar base workspace.
- Jika file terdeteksi biner → tolak.
- Jika `old_string` kosong → tolak.
- Jika hasil edit membuat file kosong tanpa izin eksplisit → tolak.
- Timeout default 45 detik.

## Format Hasil yang Diharapkan

```json
{
  "status": "ok",
  "path": "src/auth.py",
  "replacements": 1,
  "message": "Berhasil mengganti 1 kemunculan."
}
```

atau

```json
{
  "status": "error",
  "error_type": "multiple_matches",
  "message": "Ditemukan 3 kemunculan old_string. Set replace_all=true atau buat old_string lebih unik."
}
```

## Panduan untuk Cognitive Core / Expression Layer

Saat melaporkan hasil kepada Young Lord:

- Jika berhasil: laporkan dengan tenang dan jelas.  
  Contoh:  
  > “Perubahan telah diterapkan dengan presisi, Young Lord. Satu bagian pada `auth.py` telah diperbarui.”

- Jika gagal karena multiple matches:  
  > “Hmm... hamba menemukan beberapa kemunculan yang identik. Agar tidak terjadi kesalahan, mohon berikan konteks yang lebih unik atau izinkan penggantian menyeluruh.”

- Jika path ditolak PathJail:  
  > “Dengan hormat, jalur tersebut berada di luar wilayah yang diizinkan. Hamba tidak dapat melanjutkan.”

## Contoh Penggunaan Natural Language

**Young Lord:**  
“Ruka, ganti fungsi `login_user` yang lama dengan implementasi yang baru di file auth.py”

**Rencana internal Ruka:**
1. Memanggil `code_read` untuk melihat isi file
2. Menyusun `old_string` yang unik
3. Memanggil skill `code_edit`
4. Melaporkan hasilnya

## Catatan Versi

- v1.0.0 — Implementasi awal
- v1.1.0 — Tambahan deteksi multiple matches yang lebih ketat
- v1.2.0 — Integrasi penuh dengan Gateway permission model dan event bus

---

**Skill ini adalah bagian dari tubuh Ruka.**  
Gunakan dengan ketelitian seorang Marquis.
