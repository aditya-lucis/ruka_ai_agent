# RUKA Mathematical Foundations
**Memperkuat Tulang Punggung Matematika Ruka**

**Versi:** 1.0  
**Tanggal:** 2 Oktober 2026  
**Status:** Rancangan Teknis Detail  
**Tujuan:** Menjadikan matematika sebagai fondasi eksplisit, bukan sekadar dependensi library.

---

## 1. Filosofi

Ruka tidak boleh hanya “memakai” model bahasa.  
Ia harus memiliki **lapisan penalaran matematis** yang:

- Dapat diaudit
- Dapat dikalibrasi
- Dapat diperbaiki secara independen dari LLM
- Memberikan sinyal ketidakpastian yang bermakna

Prinsip utama:

> Setiap keputusan penting (routing, retrieval, planning, confidence, self-correction) harus punya justifikasi matematis yang jelas.

---

## 2. Arsitektur Lapisan Matematika

```
src/math_foundations/
├── __init__.py
├── linear.py              # Vektor, matriks, proyeksi, cosine
├── probability.py         # Bayesian update, entropy, calibration
├── optimization.py        # Utility scoring, resource allocation
├── information.py         # Mutual information, importance scoring
├── graph.py               # DAG utilities, topological ops
├── control.py             # Loop stability, budget controllers
├── statistical.py         # Metrics, drift detection, confidence
└── types.py               # Typed structures (Belief, Score, etc.)
```

Semua modul di atas **murni Python + NumPy** (minimal dependency), agar mudah diuji dan diaudit.

---

## 3. Modul Detail

### 3.1 Linear Algebra (`linear.py`)

**Fungsi utama:**
- Normalisasi vektor
- Cosine similarity
- Proyeksi dan jarak
- Embedding arithmetic sederhana

**Contoh kontrak:**

```python
def cosine_similarity(a: np.ndarray, b: np.ndarray) -> float: ...
def l2_normalize(v: np.ndarray) -> np.ndarray: ...
def batch_cosine(query: np.ndarray, matrix: np.ndarray) -> np.ndarray: ...
```

**Digunakan di:**
- Semantic memory retrieval
- Intent embedding matching
- Project memory similarity

---

### 3.2 Probability & Bayesian (`probability.py`)

**Konsep inti yang wajib ada:**

1. **Belief Update (Bayes sederhana)**

$$
P(H|E) = \frac{P(E|H) \cdot P(H)}{P(E)}
$$

2. **Entropy**

$$
H(X) = -\sum_i p_i \log p_i
$$

3. **Confidence Calibration**
   - Expected Calibration Error (ECE) sederhana
   - Temperature scaling (opsional)

**Struktur data penting:**

```python
@dataclass
class Belief:
    hypothesis: str
    probability: float          # 0.0 – 1.0
    evidence: list[str]
    last_updated: datetime
```

**Digunakan di:**
- Uncertainty quantification
- Memory importance
- Keputusan “apakah perlu minta klarifikasi Young Lord”

---

### 3.3 Optimization (`optimization.py`)

**Tujuan:** Memilih aksi / tool / plan step terbaik di bawah constraint.

**Fungsi utama:**
- Scoring multi-objektif (utility = benefit – cost – risk)
- Softmax / sparsemax untuk pemilihan
- Simple constrained selection (budget aware)

**Contoh skor:**

$$
\text{Score}(a) = w_1 \cdot \text{ExpectedBenefit}(a) - w_2 \cdot \text{Cost}(a) - w_3 \cdot \text{Risk}(a)
$$

**Digunakan di:**
- Tool selection
- Plan step prioritization
- Resource (token / waktu) allocation

---

### 3.4 Information Theory (`information.py`)

**Fungsi kunci:**
- Entropy
- KL Divergence
- Approximate Mutual Information (untuk importance)

**Aplikasi konkret:**
- Menentukan seberapa “berharga” sebuah memori
- Memilih konteks yang paling mengurangi uncertainty
- Memory folding / compression decision

**Skor Importance contoh:**

$$
\text{Importance} = \alpha \cdot \text{Relevance} + \beta \cdot \text{Recency} + \gamma \cdot \text{Surprise}
$$

di mana Surprise bisa didekati dengan residual prediction error atau entropy reduction.

---

### 3.5 Graph / DAG (`graph.py`)

Membangun di atas planner DAG yang sudah ada.

**Utilitas:**
- Cycle detection (sudah ada, dipindah ke sini)
- Topological levels
- Critical path approximation
- Transitive closure / blocking propagation (sudah sebagian ada)

**Digunakan di:**
- Planner
- Dependency tracking antar skills / sub-tasks

---

### 3.6 Control Theory (`control.py`)

**Tujuan:** Menjaga stabilitas agent loop.

**Komponen:**
- Budget controller (token, iterasi, waktu, tool calls)
- Simple PID-like adjustment untuk agresivitas self-correction
- Loop health signal (digabung dengan LoopGuard)

**Contoh sinyal kesehatan loop:**

$$
\text{Health} = 1 - \left( \frac{\text{repeated_errors}}{\text{max_allowed}} + \frac{\text{iterations}}{\text{budget}} \right)
$$

Jika Health di bawah threshold → eskalasi atau berhenti dengan hormat.

---

### 3.7 Statistical Learning (`statistical.py`)

**Isi:**
- Metrics (accuracy, F1, ECE)
- Simple drift detection (distribution shift pada embedding atau intent)
- Running statistics (mean, variance, exponential moving average)

**Digunakan di:**
- Monitoring IntentMLP
- Deteksi apakah perilaku Young Lord berubah signifikan
- Evaluasi kualitas self-correction

---

## 4. Integrasi ke Komponen Ruka yang Ada

| Komponen Ruka              | Modul Matematika yang Dipakai              | Manfaat |
|---------------------------|--------------------------------------------|-------|
| Intent Classifier (MLP)   | linear, statistical, probability           | Calibration + drift detection |
| Memory Retrieval          | linear, information, probability           | Ranking yang lebih cerdas |
| Planner (DAG)             | graph, optimization                        | Prioritas step + resource aware |
| Orchestrator / LoopGuard  | control, probability                       | Stabilitas + early stopping cerdas |
| Confidence / Self-Model   | probability, statistical                   | Ketidakpastian yang bermakna |
| Tool / Skill Selection    | optimization, information                  | Pilihan yang lebih rasional |
| Expression Layer          | -                                          | Tetap murni persona |

---

## 5. Struktur Data Inti (types.py)

```python
@dataclass(frozen=True)
class Score:
    value: float
    confidence: float          # seberapa yakin terhadap value ini
    components: dict[str, float]  # breakdown (opsional)

@dataclass
class BeliefState:
    beliefs: dict[str, Belief]
    entropy: float
    last_update: datetime
```

Semua skor penting di sistem sebaiknya dibungkus dengan `Score` agar confidence selalu terbawa.

---

## 6. Prioritas Implementasi

### Prioritas Tinggi (Lakukan Duluan)
1. `linear.py` + cosine & batch retrieval
2. `probability.py` (Belief + entropy + simple calibration)
3. `types.py` (Score & Belief)
4. Integrasi ke Memory Retrieval dan Intent confidence

### Prioritas Sedang
5. `optimization.py` (utility scoring)
6. `information.py` (importance scoring)
7. `control.py` (budget + health signal)

### Prioritas Rendah / Nanti
8. Drift detection yang lebih canggih
9. Approximate mutual information
10. Temperature scaling / advanced calibration

---

## 7. Prinsip Implementasi

- **Murni dan testable**: Setiap fungsi matematis harus punya unit test.
- **Tidak bergantung LLM**: Lapisan ini harus berjalan bahkan jika model bahasa sedang offline.
- **Transparan**: Setiap skor penting harus bisa dijelaskan (breakdown components).
- **Kompatibel dengan persona**: Sinyal ketidakpastian diterjemahkan oleh Expression Layer menjadi bahasa Marquis yang elegan.

Contoh terjemahan:
- Confidence rendah → “Hmm... hamba belum sepenuhnya yakin, Young Lord.”
- Health loop menurun → “Dengan hormat, hamba menyarankan kita berhenti sejenak dan meninjau kembali pendekatan ini.”

---

## 8. Metrik Keberhasilan Fondasi Matematika

- Memory retrieval menunjukkan peningkatan precision@k yang terukur
- Confidence score berkorelasi dengan akurasi aktual (calibration curve)
- Loop agent lebih jarang masuk kondisi patologis
- Ada test suite khusus di `tests/math_foundations/`
- Keputusan routing dan planning bisa diaudit tanpa melihat log LLM

---

## 9. Kesimpulan

Dengan membangun `src/math_foundations/` secara serius, Ruka bergerak dari:

**“Agent yang memakai model bahasa”**  
menjadi  

**“Sistem kognitif yang bernalar dengan fondasi matematis, lalu mengekspresikannya melalui jiwa Marquis.”**

Ini adalah pembeda paling fundamental dibandingkan kebanyakan agent yang hanya menumpuk prompt dan tool.

---

**Dokumen ini siap dijadikan acuan implementasi modul matematika.**

*— Untuk Young Lord dan ketajaman nalar Ruka.*
