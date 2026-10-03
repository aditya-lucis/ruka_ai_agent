# GitHub Issues — RUKA Agentic Mode

Siap copy-paste ke GitHub Issues.

---

## Issue #1 — Foundation

**Title:**  
`feat(agentic): implement Action-First Agentic Mode with personality lock`

**Labels:** `enhancement`, `agentic`, `high-priority`

**Body:**

```markdown
## Summary
Implement Mode Agentic agar Ruka **benar-benar memanggil SkillsRuntime** saat mendapat tugas coding/command, sambil tetap mempertahankan kepribadian Marquis of Trendamis.

## Problem
Saat ini ketika Young Lord memberi perintah coding (baca file, ls, edit, dll):
- Ruka hanya roleplay panjang
- Menulis teks palsu seperti `[SYSTEM_CALL: list_directory(...)]`
- Meminta user menempelkan output terminal
- SkillsRuntime tidak pernah dipanggil di jalur CLI

## Root Cause
Jalur `ruka:chat-send` → `brain.think_and_reply()` tidak pernah masuk ke SkillsRuntime. Skill hanya diceritakan di dalam prompt.

## Solution
1. Tambah aturan keras **Mode Agentic** di Doctrine
2. Pecah `think_and_reply` menjadi:
   - Mode percakapan biasa (persona penuh)
   - Mode Agentic (`_agentic_execute`)
3. Implementasi:
   - `_is_agentic_request()`
   - `_agentic_execute()`
   - `_make_simple_plan()`
   - `_wrap_agentic_result()`
4. Prinsip: **Action-First, Persona-Second**

## Acceptance Criteria
- [ ] Perintah seperti "baca package.json" atau "lihat isi folder" benar-benar memanggil skill
- [ ] Tidak lagi muncul teks `[SYSTEM_CALL: ...]`
- [ ] Jawaban akhir tetap bergaya Marquis (tenang, berwibawa, sapaan Young Lord)
- [ ] PathJail dan permission tetap aktif
- [ ] Mode chitchat / obrolan biasa tidak rusak
- [ ] Ada fallback yang elegan jika SkillsRuntime belum tersedia

## References
- `docs/RUKA_Agentic_Mode_Design.md`
- `AGENTIC_MODE_IMPLEMENTATION.md`
```

---

## Issue #2 — Orchestrator Integration

**Title:**  
`feat(agentic): integrate AgentOrchestrator + LoopGuard into Agentic Mode`

**Labels:** `enhancement`, `agentic`

**Body:**

```markdown
## Summary
Ganti simple rule-based planner dengan `AgentOrchestrator` yang sudah ada agar mendukung multi-step reasoning, self-correction, dan perlindungan LoopGuard.

## Motivation
Simple planner hanya cukup untuk 1-2 langkah. Tugas coding nyata butuh iterasi (baca → pikir → edit → test → perbaiki).

## Acceptance Criteria
- [ ] Multi-step task dapat diselesaikan dalam satu sesi
- [ ] LoopGuard membatasi iterasi dan mendeteksi loop
- [ ] Hasil akhir tetap dibungkus Expression Layer (persona Marquis)
- [ ] Budget / token control dari Math Foundations digunakan
```

---

## Issue #3 — Better Planning & Intent

**Title:**  
`feat(agentic): improve intent detection and skill planning quality`

**Labels:** `enhancement`, `agentic`, `intelligence`

**Body:**

```markdown
## Summary
Perkuat deteksi intent coding/command dan tingkatkan kualitas pemilihan skill.

## Tasks
- Perluas keyword & pola di `NeuralIntentRouter`
- Tingkatkan `_make_simple_plan` atau ganti dengan hybrid (rule + LLM)
- Pertimbangkan skill composition (satu skill memanggil skill lain)

## Acceptance Criteria
- [ ] Intent coding lebih akurat (lebih sedikit false negative)
- [ ] Skill yang dipilih lebih tepat
- [ ] Mengurangi kasus "tidak ada skill yang cocok"
```

---

## Issue #4 — Safety & Confirmation

**Title:**  
`feat(agentic): tighten confirmation flow for dangerous skills`

**Labels:** `security`, `agentic`

**Body:**

```markdown
## Summary
Saat ini `confirm_granted=True` digunakan untuk memudahkan testing. Perlu diperketat kembali untuk skill berisiko tinggi (write, delete, shell berbahaya).

## Acceptance Criteria
- [ ] Skill dengan `risk_level: high` atau `requires_confirmation: true` meminta izin Young Lord
- [ ] Alur konfirmasi tetap bergaya Marquis (hormat dan jelas)
- [ ] PathJail tidak pernah dibypass
```

---

**Cara pakai:**  
Copy masing-masing blok di atas lalu buat Issue baru di repository Ruka.
