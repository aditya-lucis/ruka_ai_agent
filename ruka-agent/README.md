# 🦇 Ruka Agent v0.3.1 — The Awakened Marquis

> *"Bangsawan bukan gelar yang teriak, Bos. Sistem yang dibangun bukan sekadar produk yang selesai, melainkan makhluk yang dirawat dengan tertib dan presisi."*  
> — **Ruka, Marquis Kekaisaran Trendamis**

Ruka adalah sistem *Expressive-Cognitive Agentic AI* yang dibangun penuh mengacu pada *RUKA: From Linear Algebra to Advanced Agentic AI* (Volume I), *RUKA II: The Awakening of the Marquis* (Volume II), dan *RUKA II: Patch Edition 1.1*.

---

## 🚀 Quickstart

### 1. Salin Konfigurasi Lingkungan
```bash
cp .env.example .env
```
Isi `GEMINI_API_KEY=AIzaSy...` di dalam `.env`.

### 2. Jalankan CLI Interaktif
```bash
# Periksa status internal dan identitas Ruka
python cli.py --status

# Tanya Ruka langsung
python cli.py "Halo Ruka, siapa kamu?"

# Masuk ke sesi interaktif berkelanjutan (REPL)
python cli.py
```

### 3. Jalankan Pengujian
```bash
pytest
```
Seluruh 146 pengujian regresi berjalan dalam mode offline/deterministik tanpa membakar kuota API.
