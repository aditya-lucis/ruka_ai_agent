# RUKA Gateway Design
**Local Control Plane untuk Ruka**

**Versi:** 1.0  
**Tanggal:** 2 Oktober 2026  
**Status:** Rancangan Teknis Mendalam  
**Inspirasi:** OpenClaw Gateway + Arsitektur Ruka yang sudah ada

---

## 1. Tujuan Gateway

Ruka Gateway adalah **proses lokal yang selalu hidup** yang berfungsi sebagai:

- Control plane tunggal untuk semua session, skills, events, dan channel
- Jembatan antara **Cognitive Core** (otak) dengan berbagai **Client** (Desktop, CLI, masa depan: Telegram, Discord, dll)
- Pengelola lifecycle agent, memory access, dan permission
- Titik sentral untuk observability dan keamanan

**Prinsip:**
> Desktop Electron dan CLI bukan lagi “pemilik” otak.  
> Mereka adalah **client** dari Gateway.

---

## 2. Arsitektur Tinggi Tingkat

```
┌─────────────────────────────────────────────────────────────────────┐
│                         RUKA GATEWAY                                │
│                    (Local Control Plane)                            │
├─────────────────────┬───────────────────────┬───────────────────────┤
│   Session Manager   │   Skills Runtime      │   Event Bus           │
├─────────────────────┼───────────────────────┼───────────────────────┤
│   Channel Adapters  │   Permission & Jail   │   Observability       │
├─────────────────────┴───────────────────────┴───────────────────────┤
│                     Cognitive Core Interface                        │
│         (RukaCognitiveBrain + Planner + Memory + Math Layer)        │
└─────────────────────────────────────────────────────────────────────┘
          ▲                    ▲                    ▲
          │                    │                    │
   ┌──────┴──────┐      ┌──────┴──────┐      ┌──────┴──────┐
   │ Desktop UI  │      │  Ruka CLI   │      │ Future      │
   │ (Electron)  │      │             │      │ Channels    │
   └─────────────┘      └─────────────┘      └─────────────┘
```

---

## 3. Komponen Internal Gateway

### 3.1 Session Manager

Setiap interaksi Young Lord berjalan di dalam **Session**.

```python
@dataclass
class Session:
    session_id: str
    channel: str                    # "desktop" | "cli" | "telegram" | ...
    user_id: str                    # biasanya "young_lord"
    created_at: datetime
    last_active: datetime
    context: dict                   # state sementara
    memory_scope: str               # "global" | "project:<path>"
    active_skills: list[str]
    metadata: dict
```

**Tanggung jawab:**
- Membuat / menghancurkan session
- Isolasi konteks antar channel
- Timeout dan cleanup session tidak aktif
- Menyimpan session state ke disk (opsional, untuk recovery)

### 3.2 Skills Runtime

Gateway mengelola lifecycle Skills.

**Alur:**
1. Discovery (scan folder skills)
2. Loading & validation (baca SKILL.md)
3. Permission check
4. Execution (dengan PathJail + timeout)
5. Result normalization

Skills dapat diaktifkan per session atau global.

### 3.3 Event Bus (Internal)

Pub/Sub sederhana di dalam proses Gateway.

**Event penting:**
- `session.created`
- `session.message`
- `skill.executed`
- `memory.updated`
- `agent.loop_started` / `agent.loop_finished`
- `health.warning`
- `permission.required`

Client bisa subscribe event tertentu (misalnya Desktop ingin tahu saat Ruka sedang berpikir).

### 3.4 Channel Adapters

Setiap channel punya adapter:

| Channel     | Adapter Responsibility                          |
|-------------|--------------------------------------------------|
| Desktop     | JSONL IPC (sudah ada, di-refactor)              |
| CLI         | Stdio / socket ringan                           |
| Telegram    | (Future) Webhook / polling                      |
| Discord     | (Future)                                       |
| Web UI      | (Future)                                       |

Adapter hanya bertugas:
- Menerima pesan mentah
- Menormalkan menjadi `InboundMessage`
- Mengirim `OutboundMessage` kembali ke channel

### 3.5 Permission & Path Jail

Gateway adalah **satu-satunya** tempat yang menegakkan:

- PathJail
- Tool/Skill permission
- Confirmation untuk aksi berbahaya
- Rate limiting sederhana

Cognitive Core **tidak** boleh langsung menyentuh filesystem atau shell tanpa melalui Gateway.

### 3.6 Observability

- Structured logging
- Metrics (latency, token usage, skill success rate, loop health)
- Trace ID per request (untuk debugging multi-step)

---

## 4. Protokol Komunikasi

### 4.1 Inbound Message (dari Client ke Gateway)

```json
{
  "type": "message",
  "session_id": "sess_abc123",
  "channel": "desktop",
  "content": {
    "text": "Perbaiki bug di auth.py",
    "attachments": []
  },
  "metadata": {
    "project_path": "/home/user/project",
    "correlation_id": "corr_456"
  }
}
```

### 4.2 Outbound Message (dari Gateway ke Client)

```json
{
  "type": "response",
  "session_id": "sess_abc123",
  "correlation_id": "corr_456",
  "content": {
    "text": "Hmm... Young Lord, hamba telah menelaah...",
    "code_blocks": [],
    "thinking": false
  },
  "events": [
    {"type": "skill.executed", "skill": "edit_file", "status": "ok"}
  ]
}
```

### 4.3 Control Messages

- `session.create`
- `session.close`
- `skill.list`
- `skill.enable` / `skill.disable`
- `health.check`
- `permission.grant`

---

## 5. Integrasi dengan Komponen yang Sudah Ada

| Komponen Lama              | Perubahan di Era Gateway                          |
|---------------------------|---------------------------------------------------|
| `launcher.py`             | Menjadi entrypoint yang menjalankan Gateway       |
| Electron IPC              | Menjadi salah satu Channel Adapter                |
| `ruka_cli.py`             | Menjadi client Gateway (bukan langsung ke brain)  |
| `RukaCognitiveBrain`      | Tetap ada, dipanggil oleh Gateway                 |
| ToolRegistry + coding.py  | Dipindah / dibungkus di bawah Skills Runtime      |
| PathJail                  | Ditegakkan di Gateway layer                       |
| Memory                    | Gateway mengatur scope (global vs project)        |

---

## 6. Lifecycle Gateway

1. **Startup**
   - Load config & doctrine
   - Initialize Mathematical Foundations
   - Load Skills
   - Start Channel Adapters
   - Start Event Bus
   - Tulis endpoint file (mirip yang sekarang)

2. **Running**
   - Menerima pesan → Session Manager → Cognitive Core → Skills → Response
   - Emit events
   - Monitor health

3. **Shutdown**
   - Graceful close semua session
   - Persist state penting
   - Cleanup

---

## 7. Keamanan

- Gateway hanya listen di `127.0.0.1` (default)
- Token autentikasi antar client dan Gateway (sudah ada polanya)
- Setiap skill/tool melewati PathJail
- Aksi berbahaya wajib confirmation (via event ke client)
- Tidak ada eksekusi remote tanpa channel yang eksplisit diizinkan

---

## 8. Struktur Folder yang Diusulkan

```
ruka-agent/
├── src/
│   ├── gateway/
│   │   ├── __init__.py
│   │   ├── server.py              # Main Gateway process
│   │   ├── session.py             # Session Manager
│   │   ├── skills/
│   │   │   ├── runtime.py
│   │   │   ├── loader.py
│   │   │   └── registry.py
│   │   ├── channels/
│   │   │   ├── base.py
│   │   │   ├── desktop.py
│   │   │   └── cli.py
│   │   ├── events.py              # Event Bus
│   │   ├── permissions.py
│   │   └── protocol.py            # Message schemas
│   ├── math_foundations/
│   ├── ruka_cognition/
│   └── ...
```

---

## 9. Migrasi Bertahap (Sangat Penting)

Jangan langsung merombak total.

**Tahap 1 – Gateway Minimal**
- Pindahkan IPC handling dari `launcher.py` ke `gateway/server.py`
- Desktop dan CLI masih bicara dengan protokol yang hampir sama
- Cognitive Core dipanggil dari Gateway

**Tahap 2 – Session & Event**
- Perkenalkan Session Manager
- Tambahkan Event Bus internal

**Tahap 3 – Skills Runtime**
- Bungkus tool coding yang sudah ada menjadi Skills
- Buat loader SKILL.md

**Tahap 4 – Multi-channel siap**
- Abstract Channel Adapter
- Siapkan tempat untuk Telegram/Discord nanti

---

## 10. Keuntungan Arsitektur Ini

| Keuntungan                         | Penjelasan                                      |
|------------------------------------|-------------------------------------------------|
| Pemisahan concern yang bersih      | Client ≠ Otak                                   |
| Siap multi-channel                 | Tinggal tambah adapter                          |
| Skills dapat diperluas             | Mirip ekosistem OpenClaw                        |
| Keamanan terpusat                  | PathJail & permission di satu tempat            |
| Observability lebih baik           | Semua lewat Event Bus                           |
| Desktop & CLI menjadi lebih ringan | Hanya UI + protokol                             |

---

## 11. Risiko & Mitigasi

| Risiko                              | Mitigasi                                         |
|-------------------------------------|--------------------------------------------------|
| Gateway jadi single point of failure| Health check + auto-restart sederhana           |
| Latency bertambah                   | Komunikasi lokal (Unix socket / TCP localhost)  |
| Migrasi merusak yang sudah jalan    | Lakukan bertahap, pertahankan protokol lama dulu|
| Kompleksitas naik                   | Mulai dari Minimal Viable Gateway               |

---

## 12. Kesimpulan

Ruka Gateway adalah fondasi arsitektur agar Ruka bisa tumbuh menjadi sistem agentic yang serius tanpa kehilangan karakter dan tanpa mengorbankan keamanan.

Dengan Gateway:
- OpenClaw-like extensibility menjadi mungkin
- Cognitive Core tetap fokus pada nalar
- Client (Desktop/CLI) tetap fokus pada pengalaman Young Lord
- Matematika dan Skills punya tempat yang jelas

---

**Dokumen ini siap dijadikan acuan implementasi Gateway.**

*— Untuk Young Lord dan masa depan Ruka yang lebih kokoh.*
