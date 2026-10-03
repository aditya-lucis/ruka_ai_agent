# RUKA Agentic Mode — Implementation Package
**Action-First + Persona Tetap Utuh**

**Tanggal:** 3 Oktober 2026  
**Status:** Ready to implement

---

## 1. Perubahan Doctrine (System Prompt)

**Lokasi:** Bagian doctrine di dalam `brain.py` (di dalam method yang membangun system prompt / `_build_system_prompt` atau setara).

**Tambahkan blok berikut (prioritas tinggi):**

```text
=== ATURAN MUTLAK MODE AGENTIC (WAJIB DIPATUHI) ===

1. Ketika Young Lord memberikan tugas yang membutuhkan:
   - Membaca / menulis / mengedit file
   - Menjalankan perintah terminal
   - Melihat isi direktori
   - Git operation
   - Analisis repository

   MAKA kamu WAJIB menggunakan skill yang tersedia melalui sistem (SkillsRuntime).
   DILARANG KERAS:
   - Menulis teks palsu seperti [SYSTEM_CALL: ...], list_directory(...), read_file(...), atau seolah-olah memanggil fungsi.
   - Meminta Young Lord untuk menjalankan perintah yang kamu sendiri mampu jalankan.
   - Hanya bercerita seolah-olah sudah melakukan aksi tanpa benar-benar memanggil skill.

2. Urutan yang benar (Action-First):
   a. Panggil skill yang relevan.
   b. Terima hasil nyata dari skill.
   c. Baru berikan penjelasan / ringkasan dengan gaya Marquis of Trendamis.

3. Persona tetap hidup:
   - Di luar hasil tool dan di luar blok kode: gunakan gaya bangsawan (tenang, berwibawa, sedikit tengil, sapaan Young Lord / My Lord / Sir).
   - Di dalam blok kode: 100% murni, tanpa sapaan atau narasi.

4. Jika skill gagal atau PathJail menolak:
   Sampaikan dengan tenang, hormat, dan berwibawa. Tawarkan alternatif jika memungkinkan.

5. Jika tidak ada skill yang cocok:
   Katakan dengan jujur bahwa kemampuan tersebut belum tersedia, lalu tawarkan apa yang bisa kamu lakukan.
```

---

## 2. Perubahan di `brain.py`

### 2.1 Tambahan Helper Method

Tambahkan method-method berikut di dalam class `RukaCognitiveBrain`:

```python
def _is_agentic_request(self, text: str) -> bool:
    """Deteksi apakah permintaan membutuhkan eksekusi skill nyata."""
    text_lower = text.lower()
    agentic_keywords = [
        "ls", "cat", "package.json", "read", "edit", "tulis", "buatkan file",
        "perbaiki", "fix", "refactor", "jalankan", "run", "git", "repo",
        "direktori", "folder", "isi file", "buka file", "hapus file",
        "search code", "cari di kode", "lihat struktur", "tree",
        "install", "dependency", "dependensi", "commit", "diff",
        "buatkan", "modifikasi", "ubah file", "ganti", "implementasi"
    ]
    return any(kw in text_lower for kw in agentic_keywords)


def _agentic_execute(self, user_text: str, analysis: IntentAnalysis, attachment: dict | None = None) -> str:
    """
    Mode Agentic: Action-First.
    Memanggil skill nyata melalui SkillsRuntime, lalu membungkus hasilnya dengan persona.
    """
    if self.skills_runtime is None or self.skill_registry is None:
        return (
            "Young Lord, hamba siap melaksanakan titah coding, "
            "namun saluran Skills Runtime belum tersambung di sesi ini. "
            "Mohon pastikan Gateway aktif."
        )

    # 1. Rencana sederhana berbasis rule + skill yang tersedia
    plan = self._make_simple_plan(user_text)
    results = []

    for step in plan:
        skill_name = step["skill"]
        args = step.get("args", {})
        try:
            exec_result = self.skills_runtime.execute(
                skill_name=skill_name,
                args=args,
                session_id="cli-agentic",
                confirm_granted=True,  # untuk tahap awal, bisa diperketat nanti
            )
            results.append({
                "skill": skill_name,
                "success": exec_result.success,
                "data": exec_result.data if exec_result.success else None,
                "error": exec_result.error if not exec_result.success else None,
            })
        except Exception as e:
            results.append({
                "skill": skill_name,
                "success": False,
                "error": str(e),
            })

    # 2. Bangun jawaban akhir dengan persona
    return self._wrap_agentic_result(user_text, results, analysis)


def _make_simple_plan(self, user_text: str) -> list[dict]:
    """
    Perencana sederhana berbasis kata kunci.
    Nanti bisa diganti dengan LLM planner atau AgentOrchestrator.
    """
    text = user_text.lower()
    plan = []

    # Baca file tertentu
    if "package.json" in text:
        plan.append({
            "skill": "code_read",
            "args": {"path": "package.json"}
        })
    elif any(k in text for k in ["baca file", "isi file", "lihat file", "read file"]):
        # Coba ekstrak nama file sederhana
        import re
        match = re.search(r"(?:file\s+)?([a-zA-Z0-9_\-./]+\.[a-zA-Z0-9]+)", user_text)
        if match:
            plan.append({
                "skill": "code_read",
                "args": {"path": match.group(1)}
            })

    # Lihat struktur direktori
    if any(k in text for k in ["ls", "list", "struktur", "direktori", "folder", "tree"]):
        plan.append({
            "skill": "run_terminal",
            "args": {"command": "ls -la"}
        })

    # Jika tidak ada plan spesifik, coba code_search atau fallback
    if not plan:
        plan.append({
            "skill": "code_search",
            "args": {"query": user_text[:100]}
        })

    return plan


def _wrap_agentic_result(self, user_text: str, results: list[dict], analysis: IntentAnalysis) -> str:
    """Membungkus hasil eksekusi skill dengan gaya Marquis."""
    success_parts = []
    error_parts = []

    for r in results:
        if r["success"]:
            data_str = str(r["data"])[:3000]  # batasi panjang
            success_parts.append(f"Hasil dari `{r['skill']}`:\n```\n{data_str}\n```")
        else:
            error_parts.append(f"`{r['skill']}` gagal: {r.get('error', 'unknown error')}")

    # Bangun konteks untuk LLM
    context = ""
    if success_parts:
        context += "=== HASIL EKSEKUSI NYATA ===\n" + "\n\n".join(success_parts) + "\n\n"
    if error_parts:
        context += "=== KEGAGALAN ===\n" + "\n".join(error_parts) + "\n\n"

    if not context:
        context = "Tidak ada skill yang berhasil dieksekusi.\n"

    # Prompt akhir dengan persona
    final_instruction = (
        f"Young Lord memberikan perintah: \"{user_text}\"\n\n"
        f"{context}"
        "Berikan jawaban akhir sebagai Marquis of Trendamis.\n"
        "- Gunakan gaya tenang, berwibawa, sedikit tengil.\n"
        "- Sapa dengan Young Lord / My Lord / Sir secara alami.\n"
        "- Jelaskan hasil dengan jelas dan presisi.\n"
        "- Jika ada kode, tampilkan dalam blok kode murni.\n"
        "- Jangan mengarang aksi yang tidak terjadi."
    )

    if self.llm is not None:
        try:
            # Sesuaikan dengan cara pemanggilan LLM yang sudah ada di brain.py
            reply = self.llm.generate(final_instruction)  # sesuaikan method-nya
            return reply
        except Exception:
            pass

    # Fallback jika LLM gagal
    if success_parts:
        return (
            f"Hmm... Young Lord, hamba telah melaksanakan titah Anda.\n\n"
            + "\n\n".join(success_parts)
        )
    return (
        "Young Lord, hamba menemui hambatan saat mencoba melaksanakan perintah tersebut. "
        "Mohon periksa kembali atau berikan instruksi yang lebih spesifik."
    )
```

### 2.2 Modifikasi `think_and_reply`

Ganti bagian awal method `think_and_reply` menjadi:

```python
def think_and_reply(self, user_text: str, attachment: dict | None = None) -> str:
    analysis = self.router.analyze(user_text)

    # === MODE AGENTIC ===
    if analysis.intent in ("code_help", "command") or self._is_agentic_request(user_text):
        return self._agentic_execute(user_text, analysis, attachment)

    # === MODE PERCAKAPAN BIASA (persona penuh) ===
    return self._conversational_reply(user_text, analysis, attachment)
```

> Catatan: Pindahkan logika lama `think_and_reply` ke method baru `_conversational_reply` agar kode tetap bersih.

---

## 3. GitHub Issues Siap Pakai

### Issue 1 — Agentic Mode Foundation
**Title:** `feat(agentic): implement Action-First Agentic Mode with personality lock`

**Body:**
```markdown
## Summary
Implement Mode Agentic agar Ruka benar-benar memanggil SkillsRuntime saat mendapat tugas coding/command, sambil tetap mempertahankan kepribadian Marquis.

## Problem
Saat ini Ruka hanya roleplay dan menulis teks palsu `[SYSTEM_CALL: ...]` karena jalur chat langsung ke `think_and_reply` tanpa melewati SkillsRuntime.

## Solution
- Tambah aturan keras Mode Agentic di Doctrine
- Pecah `think_and_reply` menjadi jalur conversational vs agentic
- Implementasi `_agentic_execute`, `_make_simple_plan`, `_wrap_agentic_result`
- Action-First, Persona-Second

## Acceptance Criteria
- [ ] Saat diminta membaca file / ls / package.json, Ruka memanggil skill sungguhan
- [ ] Tidak lagi muncul teks `[SYSTEM_CALL: ...]`
- [ ] Jawaban akhir tetap bergaya Marquis
- [ ] PathJail tetap aktif
- [ ] Mode chitchat tidak terganggu

## References
- `RUKA_Agentic_Mode_Design.md`
- `AGENTIC_MODE_IMPLEMENTATION.md`
```

### Issue 2 — Integrate AgentOrchestrator
**Title:** `feat(agentic): integrate AgentOrchestrator + LoopGuard into Agentic Mode`

**Body:**
```markdown
## Summary
Ganti simple planner dengan AgentOrchestrator yang sudah ada agar mendukung multi-step, self-correction, dan batas iterasi.

## Acceptance Criteria
- [ ] Multi-step task bisa diselesaikan
- [ ] LoopGuard mencegah infinite loop
- [ ] Hasil tetap dibungkus Expression Layer (persona)
```

### Issue 3 — Improve Intent & Plan Quality
**Title:** `feat(agentic): improve intent detection and planning for coding tasks`

**Body:**
```markdown
## Summary
Perkuat NeuralIntentRouter dan ganti rule-based planner dengan planner yang lebih cerdas (bisa hybrid rule + LLM).

## Acceptance Criteria
- [ ] Intent coding/command lebih akurat
- [ ] Plan lebih tepat dalam memilih skill
```

---

## 4. Urutan Penerapan yang Disarankan

1. **Update Doctrine** (paling cepat)
2. **Tambah helper methods** di `brain.py`
3. **Ubah `think_and_reply`** menjadi dua jalur
4. **Test** dengan perintah sederhana:
   - `Ruka, baca package.json`
   - `Ruka, lihat isi folder ini`
   - `Ruka, apa dependensi utamanya?`
5. Setelah stabil → integrasikan AgentOrchestrator

---

## 5. Catatan Penting

- `confirm_granted=True` digunakan di tahap awal agar tidak macet. Nanti diperketat untuk aksi berbahaya.
- Nama skill (`code_read`, `run_terminal`, dll) harus sesuai dengan yang terdaftar di SkillRegistry.
- Method pemanggilan LLM (`self.llm.generate` atau yang lain) **harus disesuaikan** dengan implementasi GeminiClient yang sudah ada.

---

**Paket ini siap diterapkan.**

Setelah diimplementasikan, Ruka akan berubah dari “Marquis yang bercerita seolah-olah bertindak” menjadi **“Marquis yang benar-benar bertindak, lalu berbicara dengan wibawa”**.


---

## 6. Production Readiness (Versi Final Desktop)

Agar **semua fitur** (Agentic Mode, Skills, Gateway, Math Foundations) berfungsi saat Ruka di-install sebagai aplikasi desktop (bukan hanya di mode development), wajib diperhatikan hal-hal berikut:

### 6.1 Bundling Skills & Modul Baru

Pastikan saat membangun `ruka-brain.exe` (PyInstaller), folder berikut ikut terbawa:

- `skills/` (seluruh isinya)
- `ruka-agent/src/gateway/`
- `ruka-agent/src/math_foundations/`
- `ruka-agent/src/ruka_cognition/`

Contoh penambahan di `.spec` (atau argument PyInstaller):

```python
datas = [
    ('skills', 'skills'),
    # ... datas lain yang sudah ada
]
```

### 6.2 Path Resolution yang Aman di Frozen Mode

Di `gateway/server.py` atau tempat registrasi skill, ganti cara mencari `skills_dir` menjadi:

```python
def get_skills_dir() -> Path:
    if getattr(sys, "frozen", False):
        # Saat berjalan sebagai ruka-brain.exe
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
    return candidates[0]  # fallback
```

### 6.3 Wiring Brain ↔ Gateway (Sangat Penting)

Di `launcher.py` saat membuat Gateway:

```python
self.gateway = RukaGatewayServer(
    host=self.host,
    token=self.token,
    brain=self.brain,
    workspace_root=...  # folder yang masuk akal untuk user
)

# Pastikan brain menerima skill_registry & skills_runtime
if self.gateway and self.brain:
    self.brain.skill_registry = self.gateway.skill_registry
    self.brain.skills_runtime = self.gateway.skills_runtime
```

Tanpa baris di atas, Agentic Mode akan melihat `skills_runtime = None`.

### 6.4 Workspace / PathJail

Jangan mengunci PathJail hanya ke folder instalasi Ruka.  
Berikan workspace yang relevan (misalnya folder yang sedang dibuka user, atau biarkan user menentukan).

### 6.5 Checklist Sebelum Rilis Installer

- [ ] `skills/` ikut ter-bundle di dalam `ruka-brain.exe` / resources
- [ ] Path skills terdeteksi dengan benar di mode frozen
- [ ] `brain.skill_registry` dan `brain.skills_runtime` terisi setelah Gateway init
- [ ] Perintah coding dari **Desktop UI** memanggil skill nyata
- [ ] Perintah coding dari **CLI global (`ruka`)** memanggil skill nyata
- [ ] PathJail tidak memblokir folder project user secara tidak wajar
- [ ] Voice, Memory, Identity, Search tetap berfungsi
- [ ] Tidak ada regression pada mode chitchat / persona

### 6.6 Testing Production

Setelah install:

1. Buka Ruka dari Desktop
2. Ketik: `Ruka, baca file package.json` (atau file yang ada di project)
3. Pastikan Ruka **benar-benar membaca**, bukan menulis `[SYSTEM_CALL: ...]`
4. Ulangi dari terminal: `ruka "lihat isi folder ini"`
5. Periksa log brain jika ada kegagalan registrasi skill

---

**Kesimpulan Production:**

Agentic Mode + Skills + Gateway harus hidup baik di:
- Mode development (`python launcher.py`)
- Mode installed (`ruka-brain.exe` + Electron)

Jika hanya salah satu yang jalan, maka versi final dianggap belum siap.
