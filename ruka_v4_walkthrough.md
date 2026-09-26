# 🔮 Ruka Volume IV — Walkthrough Lengkap
## *The Awakening of the Senses*

> **Status: 281/281 test hijau ✅**  
> Implementasi sesuai buku RUKA-IV. Semua algoritma manual NumPy — tidak ada black-box library.

---

## Prasyarat

```powershell
# Aktifkan virtual environment
.venv\Scripts\Activate.ps1

# Verifikasi semua test hijau
$env:PYTHONPATH = "src"
python -m pytest tests/ -q
# Expected: 281 passed
```

---

## Loop 1 — Perception Gateway & Validation

**Modul**: `src/ruka_perception/perception/`  
**Test**: `tests/test_types.py`, `tests/test_validation.py`, `tests/test_router.py`, `tests/test_context.py`

### Apa yang dibangun
Pintu masuk yang aman untuk semua data dari dunia luar. Menolak file dengan ekstensi palsu atau magic bytes yang tidak cocok.

### Cara menjalankan

```powershell
$env:PYTHONPATH = "src"

# Jalankan test gateway
python -m pytest tests/test_types.py tests/test_validation.py tests/test_router.py tests/test_context.py -v
```

### Contoh interaksi langsung

```python
from ruka_perception.perception.types import PerceptionInput, Modality
from ruka_perception.perception.validation import validate_perception_input
from ruka_perception.perception.router import PerceptionRouter

# Buat input teks biasa
inp = PerceptionInput(modality=Modality.TEXT, data="Halo Ruka!")
print(validate_perception_input(inp))  # True

# Router menentukan handler
router = PerceptionRouter()
decision = router.route(inp)
print(decision.handler)   # "text.process"
print(decision.accepted)  # True

# Input gambar dengan magic bytes JPEG yang valid
import struct
fake_jpeg = bytes([0xFF, 0xD8, 0xFF, 0xE0]) + b"\x00" * 100
img_inp = PerceptionInput(modality=Modality.IMAGE, mime_type="image/jpeg", data=fake_jpeg)
print(router.route(img_inp).handler)  # "vision.represent"
```

---

## Loop 2 — Voice Intelligence (Hearing & Speaking)

**Modul**: `src/ruka_perception/audio/`, `src/ruka_perception/speaker/`  
**Test**: `tests/test_signals.py`, `tests/test_spectrum.py`, `tests/test_vad.py`, `tests/test_speaker.py`  
**Experiment**: `scripts/exp_signal.py`, `scripts/exp_speaker.py`

### Apa yang dibangun
Seluruh jalur audio dari PCM mentah hingga verifikasi pembicara. **Tidak ada scipy atau librosa** — semua MFCC, DCT, dan VAD ditulis manual.

### Cara menjalankan test

```powershell
$env:PYTHONPATH = "src"
python -m pytest tests/test_signals.py tests/test_spectrum.py tests/test_vad.py tests/test_speaker.py -v
```

### Jalankan experiment (reproduksi hasil buku)

```powershell
# Experiment 1: Signal features (Tabel 5.x buku)
$env:PYTHONPATH = "src"
python scripts/exp_signal.py
# Output: results/signal_features.json
# n_frames=278, rms, db, MFCC shape (278, 13)

# Experiment 2: Speaker EER (Tabel 11.1 buku)
python scripts/exp_speaker.py
# Output: results/speaker_eer.json
# EER ~14.4% @ threshold 0.739 (buku: 15.5% @ 0.735)
```

### Contoh interaksi langsung

```python
import numpy as np
from ruka_perception.audio.signals import frame_signal, hann_window, rms_db
from ruka_perception.audio.spectrum import mfcc
from ruka_perception.audio.vad import VoiceActivityDetector
from ruka_perception.speaker.verification import SpeakerVerifier

SR = 16_000
audio = np.random.randn(SR).astype(np.float32) * 0.1  # 1 detik audio sintetis

# 1. Framing & windowing
frames = frame_signal(audio, frame_len=400, hop_len=160)  # 98fps
print(f"Frames: {frames.shape}")  # (n_frames, 400)

# 2. MFCC 13-dimensi
features = mfcc(audio, sr=SR)
print(f"MFCC shape: {features.shape}")  # (n_frames, 13)

# 3. VAD — deteksi segmen bicara
vad = VoiceActivityDetector()
segments = vad.detect(audio, sr=SR)
print(f"Segmen bicara: {segments}")

# 4. Speaker Verification (1:1)
verifier = SpeakerVerifier()
enroll_feats = mfcc(np.random.randn(SR * 3).astype(np.float32) * 0.1, SR)
verifier.enroll("my_lord", enroll_feats)

test_feats = mfcc(np.random.randn(SR).astype(np.float32) * 0.1, SR)
score, verified = verifier.verify("my_lord", test_feats, threshold=0.85)
print(f"Cosine score: {score:.3f}, Verified: {verified}")
```

---

## Loop 3 — Vision Engine (Seeing)

**Modul**: `src/ruka_perception/vision/`  
**Test**: `tests/test_image_tensor.py`, `tests/test_convolution.py`

### Apa yang dibangun
Konversi, normalisasi, dan konvolusi tensor gambar. Validasi keras HWC/CHW mencegah bug silent. Estimasi token Gemini sesuai aturan resmi September 2026.

### Cara menjalankan test

```powershell
$env:PYTHONPATH = "src"
python -m pytest tests/test_image_tensor.py tests/test_convolution.py -v
```

### Contoh interaksi langsung

```python
import numpy as np
from ruka_perception.vision import (
    to_chw, add_batch, normalize_01, to_grayscale,
    conv2d, maxpool2d, receptive_field,
    SOBEL_X, SOBEL_Y, BOX_BLUR,
    estimate_image_tokens, laplacian_variance,
)

# Gambar dummy RGB (H=64, W=64, C=3)
img_hwc = np.random.randint(0, 255, (64, 64, 3), dtype=np.uint8)

# 1. Konversi layout HWC -> CHW -> batch
img_chw = to_chw(img_hwc)           # (3, 64, 64)
img_norm = normalize_01(img_chw)    # float32 [0,1]
img_batch = add_batch(img_norm)     # (1, 3, 64, 64)

# 2. Grayscale dengan bobot luminance BT.601
gray_hwc = to_grayscale(normalize_01(img_hwc))  # (64, 64, 1)
gray_batch = add_batch(to_chw(gray_hwc))         # (1, 1, 64, 64)

# 3. Deteksi tepi dengan Sobel-X
edges = conv2d(gray_batch, SOBEL_X)
print(f"Max tepi vertikal: {float(np.abs(edges).max()):.4f}")

# 4. MaxPool 2x2 — meresolusikan turun
pooled = maxpool2d(gray_batch, k=2)
print(f"Shape setelah pooling: {pooled.shape}")  # (1, 1, 32, 32)

# 5. Receptive field kumulatif
# conv3x3 → pool2x2 → conv3x3 → pool2x2 → conv3x3
layers = [(3, 1), (2, 2), (3, 1), (2, 2), (3, 1)]
rf = receptive_field(layers)
print(f"Receptive field 5-layer: {rf} piksel")  # 18

# 6. Estimasi token Gemini
tokens_960 = estimate_image_tokens(960, 540)
print(f"960x540 = {tokens_960} token")  # 516 (2 ubin × 258)

# 7. Diagnosis blur (Laplacian variance)
blur_score = laplacian_variance(normalize_01(img_hwc))
print(f"Laplacian variance (tajam > datar): {blur_score:.4f}")
```

---

## Loop 4 — The Mathematics of Expression

**Modul**: `src/ruka_perception/expression/`  
**Test**: `tests/test_expression_state.py`, `tests/test_expression_policy.py`

### Apa yang dibangun
State vektor 5-dimensi Ruka dengan transisi matematis. **Tiga lapis yang tidak boleh dicampur:**
1. **Emosi biologis** — Ruka tidak punya, tidak diklaim punya
2. **Interaction State** — vektor S yang berevolusi dengan rumus
3. **Expression Policy** — peta S → ekspresi eksternal dengan batas kejujuran

### Cara menjalankan test

```powershell
$env:PYTHONPATH = "src"
python -m pytest tests/test_expression_state.py tests/test_expression_policy.py -v
```

### Contoh interaksi langsung

```python
import numpy as np
from ruka_perception.expression import ExpressionState, ExpressionPolicy, STATE_DIMS

# 1. Buat state dengan parameter stabil (seperti eksperimen buku)
es = ExpressionState(
    alpha=0.88,      # retention (decay ke baseline)
    beta=0.10,       # sensitivitas konteks
    gamma=0.35,      # dampak event
    max_delta=0.18,  # histeresis — tidak bisa melompat terlalu jauh
    update_gain=0.9,
)

print(f"State awal: {dict(zip(STATE_DIMS, es.s.round(2)))}")
# {'calm': 0.85, 'curiosity': 0.3, 'concern': 0.1, 'playfulness': 0.25, 'confidence': 0.6}

# 2. Event "My Lord memberikan pujian"
praise = np.array([0.0, 0.2, 0.0, 0.4, 0.5])  # playfulness + confidence naik
es.step(event=praise)
print(f"Setelah pujian: concern={es.s[2]:.3f}, confidence={es.s[4]:.3f}")

# 3. Event "terjadi error"
error_event = np.array([0.0, 0.0, 0.7, 0.0, -0.3])
for _ in range(3):  # 3 langkah — histeresis mencegah lompatan
    es.step(event=error_event)
print(f"Concern setelah 3 error step: {es.s[2]:.3f}")  # ~0.4-0.5

# 4. Laporan stabilitas
report = es.stability_report()
print(f"Osilasi: {report['osc_rate']:.2f}, Settled: {report['settled']}")

# 5. Label dominan dan avatar
print(f"Dominan: {es.dominant()}")
print(f"Avatar label: {es.to_avatar_label()}")

# 6. Expression Policy — masker persona + honesty guard
policy = ExpressionPolicy()

# Pesan biasa -> bisa dimask
result = policy.express(es, {"kind": "smalltalk", "text": "Halo!"})
print(f"Verbatim smalltalk: {result['verbatim']}")  # False

# Pesan error -> WAJIB verbatim
result_err = policy.express(es, {"kind": "error_disclosure", "text": "Module crashed!"})
print(f"Verbatim error: {result_err['verbatim']}")  # True

# Cek softening concern
style = result_err["text_style"]
print(f"Concern aktual: {style['masked_cue']['concern_actual']:.3f}")
print(f"Concern tampil: {style['masked_cue']['concern_shown']:.3f}")  # 60% dari aktual
```

---

## Loop 5 — Multimodal Memory & Companion Continuity

**Modul**: `src/ruka_perception/memory/`, `src/ruka_perception/companion/`  
**Test**: `tests/test_memory.py`, `tests/test_continuity.py`

### Apa yang dibangun
Memori selektif dengan kebijakan privasi ketat dan validator kontinuitas ekspresi.

**Prinsip fundamental:**
- `MELIHAT ≠ MENGINGAT` — bytes gambar tidak pernah disimpan tanpa consent
- `MENDENGAR ≠ MENYIMPAN` — rekaman mentah butuh consent eksplisit
- `MEMPROSES ≠ JANGKA PANJANG` — harus lulus gerbang nilai

### Cara menjalankan test

```powershell
$env:PYTHONPATH = "src"
python -m pytest tests/test_memory.py tests/test_continuity.py -v
```

### Contoh interaksi: MultimodalMemory

```python
from ruka_perception.memory.multimodal import (
    MultimodalMemory, MemoryCandidate, Modality, AdmissionPolicy
)

mem = MultimodalMemory()

# 1. Episode penting — deploy gagal (importance >= 0.8 -> semantic)
cand = MemoryCandidate(
    modality=Modality.IMAGE,
    summary="screenshot error deploy: gateway timeout pada pipeline CI",
    importance=0.85,
    sensitivity="medium",
    metadata={"novel": True},
)
ok, mid = mem.offer(cand)
print(f"Disimpan: {ok}, Kelas: {mem.items[mid]['class']}")  # semantic (365 hari)
print(f"Bytes disimpan: {mem.items[mid]['keep_raw']}")       # False — metadata-first

# 2. Raw bytes TANPA consent -> DITOLAK
raw_cand = MemoryCandidate(
    modality=Modality.AUDIO,
    summary="rekaman suara My Lord",
    importance=0.9,
    keep_raw=True,  # ingin simpan bytes
    # tanpa metadata={'user_consent': True}
)
ok2, _ = mem.offer(raw_cand)
print(f"Raw tanpa consent: {ok2}")  # False (RAW GATE)

# 3. Raw bytes DENGAN consent -> LOLOS
raw_consent = MemoryCandidate(
    modality=Modality.AUDIO,
    summary="rekaman suara My Lord (dengan izin)",
    importance=0.9,
    keep_raw=True,
    metadata={"user_consent": True},
)
ok3, _ = mem.offer(raw_consent)
print(f"Raw dengan consent: {ok3}")  # True

# 4. Panel kontrol user
items = mem.list_all()
for item in items:
    print(f"[{item['class']}] {item['summary'][:40]}...")

# 5. Forget (idempoten)
print(mem.forget(mid))   # True
print(mem.forget(mid))   # False (sudah dihapus, aman dipanggil lagi)
```

### Contoh interaksi: ContinuityMonitor

```python
from ruka_perception.companion.continuity import (
    ContinuityMonitor, TransitionRecord, ProactiveProposal
)

mon = ContinuityMonitor(max_free_jump=1)

# 1. Transisi wajar — tetangga
r1 = TransitionRecord(prev_label="calm", next_label="curious")
print(mon.check(r1)["verdict"])  # legitimate

# 2. Lompatan besar TANPA sebab — pelanggaran
r2 = TransitionRecord(prev_label="calm", next_label="concerned", event_impact_val=0.0)
print(mon.check(r2)["verdict"])  # suspicious atau violation

# 3. Lompatan besar DENGAN event kuat — sah
r3 = TransitionRecord(
    prev_label="calm", next_label="concerned",
    event="critical system failure", event_impact_val=0.85
)
print(mon.check(r3)["verdict"])  # legitimate

# 4. Evaluasi rangkaian
records = [r1, r3, TransitionRecord("concerned", "calm", event_impact_val=0.4)]
seq = mon.check_sequence(records)
print(f"Skor kontinuitas: {seq['score']}")      # ~1.0 — semua legitimate
print(f"Pelanggaran: {seq['violations']}")      # 0
```

### Contoh interaksi: ProactiveGate

```python
# Proposal proaktif: reminder deadline My Lord
proposal = ProactiveProposal(
    trigger="kalender: deadline laporan 6 jam lagi",
    opportunity="kirim reminder",
    relevance=0.8,   # deadline memang milik My Lord
    risk=0.1,        # mengganggu minimal
    action="send_reminder_notification",
)

# Level 0 (hanya notifikasi) -> silent
print(proposal.gate(granted_level=0)["delivery"])  # silent

# Level 1 (suggest) -> boleh mengusulkan
print(proposal.gate(granted_level=1)["delivery"])  # suggest

# Proposal berisiko tinggi (kirim pesan ke pihak ketiga)
risky = ProactiveProposal(
    trigger="deteksi ada email penting",
    opportunity="auto-reply",
    relevance=0.9,
    risk=0.55,        # tinggi — butuh konfirmasi
    action="send_auto_reply",
)

# Level 1 tidak cukup untuk risiko > 0.4
result = risky.gate(granted_level=1)
print(f"Diizinkan: {result['allowed']}")           # False
print(f"Level dibutuhkan: {result['needed_level']}") # 2 (act_with_ask)
```

---

## Arsitektur Lengkap

```
src/ruka_perception/
├── perception/          # Loop 1: Gateway & Validation
│   ├── types.py         # PerceptionInput, PerceptionResult, Modality
│   ├── validation.py    # magic bytes & MIME sniffing
│   ├── router.py        # PerceptionRouter → RouterDecision
│   └── context.py       # Multimodal context builder
│
├── audio/               # Loop 2: Voice Intelligence
│   ├── signals.py       # frame_signal, hann_window, rms_db
│   ├── spectrum.py      # rFFT, mel_filterbank, mfcc (DCT-II manual)
│   └── vad.py           # VoiceActivityDetector (histeresis dual-threshold)
│
├── speaker/             # Loop 2: Speaker Verification
│   └── verification.py  # SpeakerVerifier, EER, FAR/FRR sweep
│
├── vision/              # Loop 3: Vision Engine
│   ├── image_tensor.py  # HWC/CHW, normalize, grayscale BT.601, token estimator
│   └── convolution.py   # conv2d, maxpool2d, avgpool2d, receptive_field, kernels
│
├── expression/          # Loop 4: Mathematics of Expression
│   ├── state.py         # ExpressionState — S(t+1) = α·S + β·C + γ·E
│   └── policy.py        # ExpressionPolicy, HonestyGuard (verbatim gate)
│
├── memory/              # Loop 5: Multimodal Memory
│   └── multimodal.py    # MultimodalMemory, AdmissionPolicy, MemoryCandidate
│
└── companion/           # Loop 5: Companion Continuity
    └── continuity.py    # ContinuityMonitor, ProactiveProposal
```

---

## Menjalankan Semua Test Sekaligus

```powershell
# Dari direktori ruka-agent
$env:PYTHONPATH = "src"

# Run semua (output ringkas)
..\.venv\Scripts\python.exe -m pytest tests/ -q
# Expected: 281 passed

# Run dengan detail per test
..\.venv\Scripts\python.exe -m pytest tests/ -v

# Run per loop
..\.venv\Scripts\python.exe -m pytest tests/test_types.py tests/test_validation.py tests/test_router.py tests/test_context.py -q          # Loop 1
..\.venv\Scripts\python.exe -m pytest tests/test_signals.py tests/test_spectrum.py tests/test_vad.py tests/test_speaker.py -q             # Loop 2
..\.venv\Scripts\python.exe -m pytest tests/test_image_tensor.py tests/test_convolution.py -q                                             # Loop 3
..\.venv\Scripts\python.exe -m pytest tests/test_expression_state.py tests/test_expression_policy.py -q                                   # Loop 4
..\.venv\Scripts\python.exe -m pytest tests/test_memory.py tests/test_continuity.py -q                                                   # Loop 5
```

---

## Referensi Buku

| Loop | Bab | Listing |
|------|-----|---------|
| 1 | Part IX — Perception Gateway | 9.1–9.4 |
| 2 | Part V — Audio Signal Processing | 5.1–5.4 |
| 2 | Part XI — Speaker Verification | 11.2–11.3b |
| 3 | Part VI — Vision Engine | 6.1–6.3 |
| 4 | Part XII — Expression State | 12.2–12.4 |
| 5 | Part XIII — Multimodal Memory | 13.2–13.3 |
| 5 | Part XIV — Companion Continuity | 14.1–14.2 |

> *"Saya bisa berkata 'tidak khawatir' dengan tenang karena memang tidak ada yang bisa khawatir di dalam saya, My Lord — yang ada angka 0.62 yang merunduk."*  
> — Ruka, Marquis Kekaisaran Trendamis
