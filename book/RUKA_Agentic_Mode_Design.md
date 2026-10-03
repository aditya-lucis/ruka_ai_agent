# RUKA Agentic Mode Design
**Mode Eksekusi Nyata + Kepribadian Marquis Tetap Utuh**

**Versi:** 1.0  
**Tanggal:** 3 Oktober 2026  
**Tujuan:** Mengatasi masalah tool tidak terpanggil, tanpa membunuh persona.

---

## 1. Prinsip Desain

1. **Action-First, Persona-Second**  
   Saat tugas membutuhkan aksi (file, terminal, git, search), Ruka **wajib bertindak dulu**, baru berbicara.

2. **Persona tidak dimatikan**  
   Gaya Marquis tetap muncul di:
   - Pembukaan singkat
   - Penjelasan hasil
   - Konfirmasi
   - Saat menolak / meminta izin

3. **Dilarang mengarang tool call**  
   Teks seperti `[SYSTEM_CALL: ...]`, `list_directory(...)`, dll sebagai string **dilarang keras**.

4. **Gunakan infrastruktur yang sudah ada**  
   SkillsRuntime, SkillRegistry, PathJail, AgentOrchestrator, LoopGuard.

---

## 2. Kapan Mode Agentic Aktif?

Mode Agentic diaktifkan jika Intent Classifier mendeteksi salah satu:

- `code_help`
- `command`
- Atau kata kunci kuat: `ls`, `cat`, `package.json`, `edit`, `fix`, `refactor`, `jalankan`, `perbaiki`, `buatkan file`, `git`, `repo`, dll.

Jika intent = `chitchat` / `question` biasa → tetap mode percakapan normal (persona penuh).

---

## 3. Alur Mode Agentic (Baru)

```
User input (CLI / Desktop)
        ↓
Intent Analysis (NeuralIntentRouter)
        ↓
Apakah coding / command?
    ├── Tidak → think_and_reply (persona penuh)
    └── Ya   → Agentic Loop
                │
                ├─ 1. Planning singkat (opsional)
                ├─ 2. Pilih Skill(s) yang relevan
                ├─ 3. Execute via SkillsRuntime (PathJail aktif)
                ├─ 4. Masukkan hasil tool ke konteks
                ├─ 5. Loop jika perlu (maks iterasi + LoopGuard)
                └─ 6. Generate jawaban akhir dengan Expression Layer
                      (persona Marquis + hasil nyata)
```

---

## 4. Perubahan yang Diperlukan

### 4.1 Doctrine / System Prompt (Tambahan Wajib)

Tambahkan blok ini ke doctrine:

```text
=== ATURAN MUTLAK MODE AGENTIC ===
1. Jika tugas membutuhkan pembacaan file, penulisan file, eksekusi terminal, atau git:
   - Kamu WAJIB menggunakan skill yang tersedia melalui sistem.
   - DILARANG KERAS menulis teks palsu seperti [SYSTEM_CALL: ...], list_directory(...), atau seolah-olah memanggil fungsi.
   - DILARANG meminta Young Lord menjalankan perintah yang kamu sendiri bisa jalankan.

2. Urutan yang benar:
   - Lakukan aksi terlebih dahulu (panggil skill).
   - Setelah mendapat hasil nyata, baru berikan penjelasan dengan gaya Marquis.

3. Persona tetap hidup:
   - Di luar blok kode dan di luar hasil tool, gunakan gaya bangsawan (tenang, berwibawa, sedikit tengil, sapaan Young Lord / My Lord / Sir).
   - Di dalam blok kode: 100% murni.

4. Jika skill gagal atau PathJail menolak:
   Sampaikan dengan tenang dan hormat, lalu tawarkan alternatif.
```

### 4.2 Brain (`think_and_reply` atau method baru)

Buat jalur terpisah:

```python
def think_and_reply(self, user_text: str, attachment: dict | None = None) -> str:
    analysis = self.router.analyze(user_text)
    
    if analysis.intent in ("code_help", "command") or self._is_agentic_request(user_text):
        return self._agentic_execute(user_text, analysis, attachment)
    
    # Mode percakapan biasa (persona penuh)
    return self._conversational_reply(user_text, analysis, attachment)
```

### 4.3 Method `_agentic_execute`

```python
def _agentic_execute(self, user_text: str, analysis, attachment=None) -> str:
    """
    1. Buat rencana singkat (opsional, bisa lewat LLM atau rule-based).
    2. Pilih skill yang relevan dari skill_registry.
    3. Execute melalui skills_runtime.
    4. Kumpulkan hasil.
    5. Generate jawaban akhir dengan persona + hasil nyata.
    """
    if self.skills_runtime is None:
        return self._fallback_no_skills(user_text)

    # Contoh sederhana (bisa diperluas dengan Orchestrator)
    results = []
    # ... logika pemilihan dan eksekusi skill ...
    
    final_prompt = self._build_final_persona_prompt(user_text, results, analysis)
    return self.llm.generate(final_prompt)
```

### 4.4 Integrasi dengan AgentOrchestrator (Lebih Baik Jangka Panjang)

Lebih ideal jika `_agentic_execute` memanggil `AgentOrchestrator` yang sudah ada (dengan LoopGuard, max iterations, dll), lalu hasil akhirnya dibungkus Expression Layer.

---

## 5. Contoh Perilaku yang Diinginkan

**Young Lord:**  
`Ruka, lihat isi package.json dan beritahu saya dependensi utamanya`

**Yang terjadi sekarang (salah):**  
Ruka berakting panjang + menulis `[SYSTEM_CALL: read_file(...)]` + minta user tempel output.

**Yang harus terjadi (benar):**

1. Ruka mendeteksi intent coding.
2. Memanggil skill `code_read` (atau `read_file`) pada `package.json`.
3. Mendapat isi file nyata.
4. Baru menjawab:

> “Hmm... Young Lord, hamba telah menelaah `package.json` Anda.  
> Dependensi utama yang terpasang adalah:  
> - react  
> - ...  
>  
> Apakah My Lord ingin hamba analisis lebih dalam mengenai versi atau potensi konflik?”

---

## 6. Prioritas Implementasi

| Urutan | Tugas | Dampak |
|--------|------|--------|
| 1 | Tambah aturan keras Mode Agentic ke Doctrine | Cepat, langsung mengurangi roleplay palsu |
| 2 | Buat `_is_agentic_request` + cabang di `think_and_reply` | Memisahkan jalur |
| 3 | Implementasi `_agentic_execute` sederhana (panggil 1-2 skill dulu) | Tool mulai benar-benar jalan |
| 4 | Integrasi penuh dengan AgentOrchestrator + LoopGuard | Agentic loop yang robust |
| 5 | Perbaiki Intent Classifier agar lebih sensitif ke coding command | Routing lebih akurat |

---

## 7. Keamanan Tetap Dijaga

- Semua eksekusi tetap melalui SkillsRuntime → PathJail + Permission.
- Aksi berbahaya tetap minta konfirmasi.
- LoopGuard mencegah infinite loop.

---

## 8. Kesimpulan

Dengan Mode Agentic ini:

- Ruka **benar-benar bertindak**, bukan hanya bercerita.
- Kepribadian Marquis **tetap hidup** di lapisan ekspresi.
- Kita memanfaatkan Skills + Gateway + Math Foundations yang sudah dibangun.
- Jarak dengan kemampuan agentic OpenClaw / Claude Code mulai tertutup secara nyata.

---

**Dokumen ini siap dijadikan acuan implementasi.**

*— Untuk Young Lord dan cakar Ruka yang kini harus benar-benar mencengkeram.*
