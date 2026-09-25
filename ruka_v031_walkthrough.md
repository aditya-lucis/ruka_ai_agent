# 🦇 Panduan Penggunaan Ruka v0.3.1 — The Awakened Marquis

> *"Bangsawan bukan gelar yang teriak, Bos. Sistem yang dibangun bukan sekadar produk yang selesai, melainkan makhluk yang dirawat dengan tertib dan presisi."*  
> — **Ruka, Marquis Kekaisaran Trendamis**

Dokumen ini adalah panduan praktis dan operasional untuk menggunakan, menguji, dan mengembangkan **Ruka Agent v0.3.1**, arsitektur *Expressive-Cognitive Agentic AI* yang telah dibangun penuh sesuai standar teknis *RUKA I*, *RUKA II: The Awakening of the Marquis*, dan *RUKA II: Patch Edition 1.1*.

---

## 1. Persiapan Lingkungan (*Quickstart*)

### 1.1 Salin Konfigurasi `.env`
Ruka menggunakan parser `.env` mandiri (stdlib-only tanpa ketergantungan eksternal) dengan penegakan *fail-fast* saat startup.

```bash
cd ruka-agent
cp .env.example .env
```

Pastikan variabel utama diatur di `.env`:
```ini
GEMINI_API_KEY=AIzaSy...              # Kunci resmi Google Gemini API
RUKA_ENVIRONMENT=development         # development | staging | production
RUKA_MODEL=gemini-3.8-flash           # Model penalaran utama
RUKA_TTS_MODEL=gemini-3.1-flash-tts-preview
RUKA_VOICE=Sulafat                   # Suara resmi Ruka (bariton tenang & mantap)
RUKA_LIVE_MODEL=gemini-3.1-flash-live-preview
RUKA_MAX_ITERATIONS=12               # Batas putaran LoopGuard
RUKA_TOKEN_BUDGET=60000              # Anggaran token per request
```

---

## 2. Cara Menggunakan CLI Interaktif

Ruka v0.3.1 dilengkapi dengan antarmuka baris perintah resmi (`cli.py`) yang menghubungkan seluruh 16 lapisan arsitektur.

### 2.1 Memeriksa Status & Identitas Internal Ruka
Melihat identitas *self-model*, status emosi VAD saat ini (*Valence, Arousal, Dominance*), profil suara, dan fase mesin status (FSM):

```bash
python cli.py --status
```
*Contoh Keluaran:*
```text
  ____  _   _ _  __    _       ___ _____ _   
 |  _ \| | | | |/ /   / \     / _ \_   _/ \  
 | |_) | | | | ' /   / _ \   | | | || |/ _ \ 
 |  _ <| |_| | . \  / ___ \  | |_| || / ___ \
 |_| \_\\___/|_|\_\/_/   \_\  \___/ |_/_/   \_|
  RUKA v0.3.1 — The Awakened Marquis (Trendamis)
  Cognitive-Expressive Agentic Architecture
  =============================================

[*] Identitas  : Ruka (Marquis, Kekaisaran Trendamis)
[*] Spesies    : vampire_cat
[*] Versi      : v0.3.0
[*] Voice TTS  : Sulafat (deep, steady, gentle cadence)
[*] Emosi VAD  : [Valence=0.00, Arousal=0.20, Dominance=0.60]
[*] Ekspresi   : neutral
[*] FSM Phase  : idle
```

### 2.2 Menjalankan Perintah / Pertanyaan Langsung
Menjalankan evaluasi satu kalimat cepat (*single turn*) dengan metrik latensi dan ID jejak audit (*trace ID*):

```bash
python cli.py "Halo Ruka, siapa kamu?"
```
*Contoh Respon:*
```text
[Ruka (focused, know)]: Saya Ruka, Marquis. Sistem agentic kognitif-ekspresif v0.3.0. Saya melayani Bos dengan ketertiban lima abad, bukan teater.
(Latency: 0.0ms | Trace: 473cd80fa83d)
```

### 2.3 Mode Dialog Interaktif (REPL)
Memulai sesi percakapan berkelanjutan dengan respons afektif dinamis:

```bash
python cli.py
```
```text
Mode interaktif aktif. Ketik 'exit' atau 'keluar' untuk mengakhiri.
Ruka siap mendengarkan.

Bos > Ruka! Tolong rancang skema database untuk proyek kita
Ruka [focused|uncertain]: Perintah diterima dengan status PLANNED. Seluruh parameter dependensi dan pagu anggaran telah diamankan. Langkah siap dijalankan. (saya tidak yakin: bukti bercampur/lemah)
      ⤷ [Intent: task_request | Complexity: planned | Latency: 1.2ms | ID: b84f1a239c01]

Bos > keluar
Ruka: 'Selamat beristirahat, Bos. Istana tetap terjaga. Yes, Sir!'
```

---

## 3. Cara Menggunakan Ruka dalam Kode Python

Anda dapat mengintegrasikan komponen Ruka secara langsung ke dalam aplikasi atau skrip Python Anda:

### 3.1 Integrasi Aplikasi Utuh (`RukaApp`)
```python
from src.application.ruka_app import RukaApp

# Inisialisasi stack lengkap (Tools, Memory, RAG, Planner, Evaluator)
app = RukaApp()

# Kirim permintaan
user_id = "user-aditia"
response = app.handle(user_id=user_id, request="Hitung 15 * 24 lalu simpan catatan ini")
print(response)
```

### 3.2 Menggunakan Perencanaan Terstruktur (DAG & Checkpoint)
```python
from src.agent.planner import PlanRecord, PlanStep, PlanStore, resume

# Bangun graf dependensi (DAG)
plan = PlanRecord(plan_id="p-001", goal="Analisis Log Produksi")
plan.steps["fetch"] = PlanStep("fetch", "Unduh berkas log dari server")
plan.steps["parse"] = PlanStep("parse", "Filter error 5xx", depends_on=["fetch"])
plan.steps["report"] = PlanStep("report", "Tulis ringkasan eksekutif", depends_on=["parse"])

# Validasi tidak ada siklus (Cycle detection)
plan.validate()

# Simpan ke checkpoint SQLite
store = PlanStore("plans.db")
store.save(plan)

# Lanjutkan eksekusi dari checkpoint tanpa mengulang langkah DONE
# resume(plan, executor, store)
```

### 3.3 Menjalankan Evaluasi Diri (Crimson Reflection)
```python
from src.reflection.loop import ReflectionLoop, CheckKind, CheckVerdict, Severity, CorrectionPlan

def custom_checker(draft: str, kind: CheckKind) -> CheckVerdict:
    if kind == CheckKind.VALIDATION and len(draft) < 10:
        return CheckVerdict(kind=kind, severity=Severity.MAJOR, problem="Jawaban terlalu pendek")
    return CheckVerdict(kind=kind, severity=Severity.PASS)

def custom_corrector(draft: str, problems: list[CheckVerdict]) -> CorrectionPlan:
    return CorrectionPlan(revised_answer=draft + " (diperjelas dengan konteks lengkap)")

loop = ReflectionLoop(custom_checker, custom_corrector)
report = loop.run("Singkat.")
print("Jawaban akhir:", report.final_answer)
print("Koreksi terpakai:", report.corrections_used)
```

---

## 4. Memeriksa Telemetri & Jejak Audit (*Forensic Traces*)

Setiap interaksi dicatat secara deterministik dalam berkas JSONL di folder `logs/` dengan skema 16 bidang terpadu (redaksi otomatis nomor kartu, email, dan kunci Gemini `AIza...`):

```bash
# Memeriksa berkas log trace hari ini
cat logs/ruka-20260925.jsonl
```

Format setiap baris JSONL memuat:
- `trace_id`, `session_id`, `ts`, `goal`
- `final_status` (`done`, `partial`, `budget_stopped`, `refused`)
- `summary`: ringkasan intent, kompleksitas, token, latensi, dan keyakinan
- `events`: linimasa mikro-detik setiap lapisan (*FSM, Emotion, Neural, Policy, Sandbox, Tool, Reflection*)

---

## 5. Menjalankan Seluruh Rangkaian Pengujian (*Regression Suite*)

Untuk memastikan seluruh arsitektur bekerja 100% tanpa regresi:

```bash
# Menjalankan seluruh 146 unit dan integration tests
pytest
```
*Hasil:*
```text
============================= 146 passed in 3.67s =============================
```

Semua 146 pengujian berjalan dalam mode deterministik/hermetic offline tanpa membakar kuota API eksternal.
