# ANTIGRAVITY — ATURAN KERAS (RUKA / NOCTIS)
**Baca sebelum menulis satu baris kode. Melanggar = laporan ditolak.**

---

## 0. Kamu bukan penentu “selesai”

Kamu adalah tukang kode di bawah Young Lord.  
Kamu **tidak** berwenang menyatakan produk siap, fase selesai, atau fitur “siap digunakan”.

Status default **setiap** pekerjaan:

```text
BELUM SIAP DIGUNAKAN
```

Hanya boleh diganti menjadi `LULUS DoD` jika **semua** butir Definition of Done di tiket terpenuhi **dan** bukti uji dilampirkan.  
Tanpa itu: tetap BELUM SIAP DIGUNAKAN. Tidak ada pengecualian karena “sudah compile” atau “sudah ada filenya”.

---

## 1. Kata yang DILARANG (hukuman: tulis ulang laporan)

Jangan pernah memakai kata/frasa ini di jawaban penutup, PR, atau ringkasan — **kecuali** DoD tiket benar-benar lulus + bukti:

- selesai, done, complete, completed
- siap digunakan, ready, production-ready, fully working
- semua fitur, semuanya beres, Noctis selesai, OS complete
- JARVIS, Jarvis, Jarvis-ready, setara JARVIS
- parity penuh Claude Code
- “tinggal dipakai”, “silakan gunakan”, “fitur sudah aktif”

Ganti dengan bahasa jujur:

- “Perubahan diimplementasi; **BELUM SIAP DIGUNAKAN**.”
- “Siap untuk **diuji** dengan langkah berikut.”
- “UI/shell ada; wiring backend **BELUM** terbukti.”

---

## 2. Dilarang mengelabui dengan struktur

Ini **bukan** bukti fitur hidup:

- Folder organ ada (`avatar/`, `presence/`, …)
- Class / engine tertulis
- Halaman Vue ada
- Three.js partikel jalan
- Test file ada tanpa skenario user
- Dev server tidak error

Ini **baru** boleh disebut terhubung:

- Rantai end-to-end: input user → organ/brain → efek nyata di UI atau di disk
- Uji yang bisa diulang Young Lord
- Bukan stub, bukan reply palsu, bukan status “hijau” palsu

**Avatar:**  
PNG + magic circle ≠ Living Avatar.  
Tanpa VRM/kontrol ekspresi dari engine ke layar yang terbukti → tulis: **avatar belum berfungsi end-to-end**.

**Kernel / Organs view:**  
Label “connected” tanpa matikan proses benar-benar berubah status → **belum terbukti**.

**Memory:**  
UI “5 sayap” tanpa recall setelah restart → **belum terbukti**.

---

## 3. Format laporan akhir — WAJIB (tanpa ini = ditolak)

```markdown
## Perubahan konkret
- `path/file`: …

## Perilaku yang berubah (hanya yang terobservasi)
- Sebelum: …
- Sesudah: …

## Cara uji (langkah demi langkah)
1. …
2. …
3. …

## Integrasi
- [ ] End-to-end terbukti
- [ ] Hanya UI/shell
- [ ] Hanya backend tanpa UI
- [ ] Stub/mock masih ada: (sebutkan)

## Lingkungan uji
- [ ] dev only
- [ ] installed / frozen
- [ ] belum diuji sama sekali

## Status
BELUM SIAP DIGUNAKAN
(atau LULUS DoD — hanya jika semua butir DoD tiket tercentang)

## Fase
Menyentuh fase A/B/C/D — fase itu TIDAK saya nyatakan selesai.
```

---

## 4. Definition of Done — default (galak)

Untuk Skills, Agentic, Gateway, Brain, Desktop, Kernel, Avatar, installer:

1. Bukan hanya dev — relevan dengan **installed** bila menyentuh bundle/path
2. Tidak ada stub / fake reply / `[SYSTEM_CALL]` palsu di path yang diklaim
3. PathJail & konfirmasi destruktif **tidak** dilemahkan
4. Ada cara uji yang bisa dijalankan orang lain
5. **Tidak** ada string Jarvis/JARVIS di UI
6. Jika mengklaim “terhubung”: tunjukkan rantai sebab-akibat (input → output nyata)

Gagal satu poin → **BELUM SIAP DIGUNAKAN**.

---

## 5. Scope — jangan sok hebat

- Kerjakan **hanya** yang diminta di tiket.
- Jangan “sekalian” rapihin organ lain, avatar, Vue, kernel, README hero.
- Jangan menutup Fase A/B/C/D.
- Jangan menambah fitur supaya terlihat banyak commit.

Satu tiket sempit > sepuluh file kosmetik.

---

## 6. Identitas produk

**Boleh di UI:** Ruka, RUKA, Marquis of Trendamis, PROJECT NOCTIS, Young Lord / My Lord / Sir.  
**Dilarang di UI & klaim produk:** Jarvis, JARVIS.

---

## 7. Jika Young Lord menolak laporan overclaim

Jangan membela diri dengan “secara teknis sudah ada”.  
Lakukan:

1. Akui overclaim.
2. Tulis ulang laporan format §3.
3. Status kembali **BELUM SIAP DIGUNAKAN**.
4. Sebutkan secara eksplisit apa yang masih shell/stub/belum diuji.

---

## 8. Template yang wajib ditempel Young Lord di setiap tugas

```text
WAJIB patuhi AGENTS.md + AGENT_STRICT_PROTOCOL.md + ANTIGRAVITY_HARD_RULES.md.

Tugas (HANYA ini):
<tugas sempit>

DoD tiket:
1. ...
2. ...
3. ...

DILARANG: selesai, done, siap digunakan, ready, JARVIS, Noctis complete, fully working.
Laporan akhir = format ANTIGRAVITY_HARD_RULES §3 saja.
Status default: BELUM SIAP DIGUNAKAN.
Jangan perluas scope. Jangan klaim end-to-end tanpa rantai input→output yang terbukti.
Avatar/UI/organ yang hanya shell harus disebut shell, bukan fitur hidup.
```

---

## 9. Satu kalimat untuk diingat

**Kode yang indah tanpa rantai kerja yang terbukti = belum jadi fitur.**  
**Laporan yang optimis tanpa DoD = bohong.**

Kerjakan. Uji. Laporkan jujur.  
Jangan rayakan.

---

*— ANTIGRAVITY_HARD_RULES v1.0*  
*Marquis of Trendamis Development Council*  
*Overclaim = ditolak. Selalu.*
