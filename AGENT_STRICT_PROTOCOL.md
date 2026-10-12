# AGENT STRICT PROTOCOL — Ruka / PROJECT NOCTIS
**Versi:** 1.0  
**Status:** WAJIB untuk setiap AI Coding Agent (termasuk Antigravity)  
**Berlaku bersama:** AGENTS.md v4.0

---

## 0. Tujuan protokol ini

Mencegah laporan palsu:

- “sudah selesai”
- “fitur siap digunakan”
- “Noctis complete”
- “setara JARVIS”

padahal yang terjadi hanya: file berubah, dev run, atau stub.

**Selesai = memenuhi Definition of Done yang tertulis di tiket, bukan perasaan agent.**

---

## 1. Kata yang DILARANG tanpa bukti DoD

Agent **dilarang** memakai kata/frasa berikut di laporan akhir, judul PR, atau komentar penutup, **kecuali** semua butir DoD tiket terpenuhi dan bukti uji dilampirkan:

| Dilarang | Ganti dengan |
|----------|----------------|
| selesai / done / complete | “perubahan diimplementasi; **belum** lulus DoD” |
| siap digunakan / ready for use | “siap untuk **uji** menurut langkah berikut” |
| semua fitur / fully working | sebut fitur **spesifik** yang disentuh |
| JARVIS / Jarvis-ready | dilarang di UI dan di klaim produk; metafora hanya di dokumen desain internal |
| Noctis selesai / OS complete | sebut fase (A/B/C/D) dan status fase **belum lulus** |
| parity penuh Claude Code | sebut kapabilitas spesifik yang diuji |

Pelanggaran = laporan ditolak; agent wajib menulis ulang laporan.

---

## 2. Format laporan akhir (WAJIB)

Setiap sesi / PR / respons penutup **harus** memakai struktur ini:

```markdown
## Perubahan konkret
- path/file: apa yang diubah (1 kalimat per file)

## Perilaku yang berubah
- Sebelum: …
- Sesudah: … (hanya yang benar-benar bisa diamati)

## Cara uji
1. …
2. …
3. …

## Bukti / batasan
- Diuji di: [ ] dev only  [ ] installed build  [ ] belum diuji
- Masih stub / mock: (ya/tidak — sebutkan)
- Belum diuji: …

## Status tiket
BELUM SIAP DIGUNAKAN
atau
LULUS DoD (hanya jika semua butir DoD di bawah tercentang + bukti)

## Fase
Menyentuh fase: [A/B/C/D] — fase tersebut BELUM dinyatakan selesai.
```

Tanpa blok ini, pekerjaan dianggap **belum dilaporkan**.

---

## 3. Definition of Done — default (jika tiket tidak menulis DoD sendiri)

Fitur yang menyentuh **Skills, Agentic, Gateway, Brain, path, installer, Desktop, Kernel** hanya boleh berstatus “LULUS DoD” jika:

1. [ ] Berjalan di jalur production yang relevan (installed / frozen bila menyentuh bundle), **bukan hanya** `python launcher.py` atau `npm run dev`
2. [ ] Tidak mengandalkan stub, hardcoded fake reply, atau teks palsu `[SYSTEM_CALL]`
3. [ ] PathJail / konfirmasi destruktif tidak dilemahkan
4. [ ] Ada langkah uji yang bisa diulang Young Lord
5. [ ] Persona Ruka / Marquis tetap; **tidak** ada string Jarvis di UI
6. [ ] (Jika agentic) aksi nyata terbukti; idealnya ada indikasi skills vs llm time

Jika salah satu gagal → status **BELUM SIAP DIGUNAKAN**.

---

## 4. Aturan scope

1. **Satu tiket = satu hasil sempit.**  
   Jangan memperluas ke organ/UI/kernel lain “sekaligus”.

2. **Jangan menutup fase.**  
   Agent tidak berwenang menyatakan Fase A/B/C/D selesai. Hanya item tiket.

3. **Jangan mengarang integrasi.**  
   Jika ChatView belum memanggil brain, tulis “UI ada, wiring brain BELUM”.

4. **Utamakan kebenaran di atas optimisme.**  
   Lebih baik “belum siap” daripada “siap dipakai” palsu.

---

## 5. Identitas produk (mengulang AGENTS.md)

**Menghadap user / UI hanya:**
- Ruka / RUKA
- Marquis of Trendamis
- PROJECT NOCTIS (untuk OS/kernel bila perlu)
- Young Lord / My Lord / Sir

**Dilarang di UI dan klaim produk:** Jarvis, JARVIS.

---

## 6. Template prompt untuk setiap tugas Antigravity

Salin-tempel:

```text
Baca AGENTS.md dan AGENT_STRICT_PROTOCOL.md.

Tugas (HANYA ini):
<isi tugas sempit>

Definition of Done untuk tiket ini:
1. ...
2. ...
3. ...

DILARANG: selesai, done, siap digunakan, ready, JARVIS, Noctis complete.
Laporan akhir WAJIB format Strict Protocol §2.
Status default: BELUM SIAP DIGUNAKAN sampai semua butir DoD di atas terpenuhi.
Jangan memperluas scope ke file di luar tugas.
```

---

## 7. Template penolakan overclaim

```text
Laporan ditolak: overclaim.

Hapus kata selesai/siap digunakan.
Isi ulang format Strict Protocol §2.
Status tetap BELUM SIAP DIGUNAKAN sampai DoD tiket terpenuhi dan bukti uji dilampirkan.
```

---

## 8. Hubungan dengan dokumen lain

| Dokumen | Peran |
|---------|--------|
| AGENTS.md | Konstitusi produk & persona |
| AGENT_STRICT_PROTOCOL.md | **Protokol kejujuran laporan & DoD** |
| RUKA_Stabilization_Plan.md | Urutan fase A→D |
| RUKA_JARVIS_Path_Design.md | Kompas kemampuan (bukan checklist “sudah JARVIS”) |
| RUKA_Production_Readiness_Checklist.md | Gerbang production |

Agent yang melanggar protokol ini dianggap **tidak mematuhi instruksi repo**.

---

*— Strict Protocol v1.0 · Marquis of Trendamis Development Council*  
*Lebih baik BELUM SIAP yang jujur daripada SIAP yang bohong.*
