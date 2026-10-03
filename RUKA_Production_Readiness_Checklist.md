# RUKA Production Readiness Checklist
**Memastikan setiap fitur benar-benar hidup setelah instalasi di desktop lokal**

**Versi:** 1.0  
**Tanggal:** 3 Oktober 2026  
**Tujuan:** Menghindari kesalahan sebelumnya di mana fitur hanya jalan di development.

---

## 1. Prinsip Utama

> **Fitur belum selesai jika hanya jalan di `python launcher.py`.**  
> Fitur baru dianggap selesai **hanya jika** berfungsi di versi yang di-install (Ruka Setup / ruka-brain.exe + Electron).

Setiap perubahan terkait:
- Agentic Mode
- Skills System
- Gateway
- Math Foundations
- Path / Workspace

**wajib** lulus checklist di bawah ini sebelum dianggap siap rilis.

---

## 2. Risiko yang Sering Terjadi (Harus Ditutup)

| Risiko | Gejala di Versi Installed | Dampak |
|--------|---------------------------|--------|
| Skills folder tidak ter-bundle | Skill tidak ketemu / registry kosong | Agentic Mode mati |
| Path salah di frozen mode (`sys._MEIPASS`) | `skills_dir` mengarah ke lokasi kosong | Skill gagal load |
| Brain tidak menerima `skills_runtime` | `skills_runtime is None` | Hanya roleplay lagi |
| PathJail mengunci ke folder instalasi | Tidak bisa baca project user | Coding agent tidak berguna |
| Gateway gagal init diam-diam | Fallback tanpa error jelas | Fitur hilang tanpa peringatan |
| CLI global vs Desktop beda perilaku | Satu jalan, satu tidak | Pengalaman tidak konsisten |

---

## 3. Checklist Bundling (PyInstaller / Installer)

### 3.1 Data Files yang Wajib Ikut

Pastikan masuk ke dalam `ruka-brain.exe` atau resources:

- [ ] Folder `skills/` (seluruh isinya, termasuk setiap `SKILL.md`)
- [ ] `ruka-agent/src/gateway/`
- [ ] `ruka-agent/src/math_foundations/`
- [ ] `ruka-agent/src/ruka_cognition/`
- [ ] Modul agent, tools, dll yang dibutuhkan

**Contoh di `.spec`:**
```python
datas = [
    ('skills', 'skills'),
    # ... datas lain
]
```

### 3.2 Verifikasi Setelah Build

Setelah membangun installer / `ruka-brain.exe`:

```bash
# Cek apakah skills ikut terbawa
# (sesuaikan path sesuai struktur hasil build)
dir resources\brain\skills
# atau
dir _internal\skills
```

- [ ] Folder `skills` ada dan berisi `code_read`, `code_edit`, `run_terminal`, dll.

---

## 4. Checklist Path Resolution (Frozen Mode)

### 4.1 Fungsi yang Wajib Ada

```python
def get_skills_dir() -> Path:
    if getattr(sys, "frozen", False):
        candidates = [
            Path(sys._MEIPASS) / "skills",
            Path(sys.executable).resolve().parent / "skills",
            Path(sys.executable).resolve().parent / "resources" / "skills",
        ]
    else:
        candidates = [
            Path(__file__).resolve().parent.parent.parent.parent / "skills",
            Path.cwd() / "skills",
        ]
    for c in candidates:
        if c.exists() and c.is_dir():
            return c
    return candidates[0]
```

- [ ] Fungsi di atas (atau setara) digunakan saat registrasi skill
- [ ] Tidak hardcode path development

### 4.2 Workspace / PathJail

- [ ] `workspace_root` yang diberikan ke Gateway / PermissionManager **bukan** folder instalasi Ruka
- [ ] User bisa bekerja di project mereka sendiri
- [ ] PathJail tetap mencegah akses di luar batas yang diizinkan

---

## 5. Checklist Wiring Brain ↔ Gateway

Di `launcher.py` (atau setara di frozen entrypoint):

```python
self.gateway = RukaGatewayServer(
    host=self.host,
    token=self.token,
    brain=self.brain,
    workspace_root=workspace_root,  # yang masuk akal
)

if self.gateway and self.brain:
    self.brain.skill_registry = self.gateway.skill_registry
    self.brain.skills_runtime = self.gateway.skills_runtime
```

- [ ] `brain.skill_registry` terisi setelah init
- [ ] `brain.skills_runtime` terisi setelah init
- [ ] Jika Gateway gagal, ada log yang jelas (bukan gagal diam-diam)

---

## 6. Checklist Agentic Mode di Production

Setelah Ruka di-install:

### Dari Desktop UI
- [ ] Perintah: “Ruka, baca package.json” → benar-benar membaca file (bukan menulis `[SYSTEM_CALL]`)
- [ ] Perintah: “lihat isi folder ini” / “ls” → memakai skill sungguhan
- [ ] Jawaban akhir tetap bergaya Marquis
- [ ] Tidak meminta user menempelkan output terminal

### Dari CLI Global (`ruka`)
- [ ] `ruka "baca package.json"` berperilaku sama dengan Desktop
- [ ] `ruka status` menunjukkan gateway/skills aktif (jika ada indikator)

### Negative Test
- [ ] Tidak muncul lagi teks palsu `[SYSTEM_CALL: ...]`
- [ ] Jika skill gagal, pesan error tetap bergaya Marquis dan jelas

---

## 7. Checklist Fitur Lain yang Tidak Boleh Rusak

Setelah instalasi, pastikan tetap berfungsi:

- [ ] Voice (TTS + ASR)
- [ ] Memory (episodic / semantic / identity)
- [ ] Google Search (jika diaktifkan)
- [ ] Desktop UI + Tray
- [ ] Mode chitchat / persona biasa
- [ ] PathJail masih menolak path berbahaya

---

## 8. Prosedur Verifikasi Sebelum Rilis

1. Build installer / portable terbaru
2. Install di mesin bersih (atau virtual machine)
3. Jalankan Ruka dari Start Menu / Desktop
4. Jalankan test suite manual di atas (bagian 6 & 7)
5. Cek log brain (`%LOCALAPPDATA%\ruka\logs\`) jika ada kegagalan
6. Baru anggap fitur **production-ready**

---

## 9. Aturan untuk Kontributor & AI Agent

Ditambahkan ke `AGENTS.md`:

> Setiap fitur yang menyentuh Skills, Gateway, Agentic Mode, atau path resolution  
> **wajib** menyertakan catatan production readiness dan lulus checklist ini  
> sebelum di-merge / dianggap selesai.

Jangan pernah menganggap “sudah jalan di dev” sebagai cukup.

---

## 10. Ringkasan

| Aspek | Yang Harus Benar |
|-------|------------------|
| Bundling | `skills/` dan modul baru ikut ter-bundle |
| Path | Benar di frozen mode (`sys._MEIPASS` dll) |
| Wiring | Brain menerima `skill_registry` + `skills_runtime` |
| Workspace | PathJail mengizinkan project user |
| Testing | Diuji di versi **installed**, bukan hanya dev |
| Persona | Tetap hidup setelah aksi nyata |

---

**Dokumen ini adalah pagar pengaman.**  
Tujuannya agar Ruka yang dipegang Young Lord di desktop benar-benar memiliki cakar yang tajam, bukan hanya cerita tentang cakar.

*— Marquis of Trendamis Development Council*
