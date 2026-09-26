# 🩸 RUKA Volume III: Crimson Cognition — Development Plan

Sesuai dengan blueprint dari `book/RUKA-III-Crimson-Cognition.pdf`, iterasi ini membawa Ruka naik kelas dari agen berbasis LLM menjadi **Sistem Kognitif Hibrida** (Hybrid Cognitive Architecture). Kita akan membangun subsistem matematis murni menggunakan NumPy (tanpa PyTorch) yang beroperasi sebelum LLM membuat keputusan, memastikan determinisme, efisiensi token, dan visibilitas metrik.

---

## 🎯 Tujuan Utama (The Goal)
Membangun paket `ruka_cognition` yang independen, lulus 126/126 pengujian ketat (*invariants, exact index, gradient checking*), dan menghubungkannya dengan `ruka-agent` tanpa menghancurkan fondasi Volume II.

## 🗺️ Peta Langkah (Phases)

### 🧱 Phase 1: Matematika Dasar & Vector Intelligence (Blood Sight)
*Membangun fondasi metrik dan pencarian vektor deterministik.*
- [ ] Buat modul kernel kemiripan: `ruka_cognition/vector/similarity.py` (dot product, cosine, euclidean, l2_norm).
- [ ] Buat antarmuka penyedia (*provider*): `ruka_cognition/vector/interfaces.py`.
- [ ] Implementasikan penyedia: `GeminiEmbeddingProvider` dan `HashedNGramEmbeddingProvider` (untuk pengujian deterministik).
- [ ] Bangun `VectorIndex` (pencarian *brute-force* eksak) & *deduplication*.
- [ ] Implementasikan `RecencyRanker` dan `MMRSelector` (Maximal Marginal Relevance).
- [ ] Uji Invarian (*Scale, Bound, Triangle Inequality*).

### 🧠 Phase 2: Context & Tool Intelligence (Shadow Step)
*Membangun filter logika sebelum membebani *context window* LLM.*
- [ ] Bangun `ContextRelevanceEngine`: Skor komposit 5 faktor (similarity, recency, importance, task, source) dengan pembatasan anti-bias.
- [ ] Bangun resolusi konflik memori (`detect_conflicts`).
- [ ] Implementasikan `ToolIntelligence`: Pra-pemeringkatan (*pre-ranking*) deterministik untuk kapabilitas *tools* berdasarkan cakupan (coverage) dan penalti risiko.

### ⚙️ Phase 3: Neural Subsystem (Ancient Mind)
*Jaringan saraf murni dengan NumPy untuk klasifikasi intent & kompleksitas berbiaya rendah.*
- [ ] Bangun arsitektur layer `Dense` berserta *forward* dan *backward pass*.
- [ ] Implementasikan aktivasi stabil (ReLU, Sigmoid, Tanh, Softmax max-shift) & *Losses* (MSE, BCE, CCE).
- [ ] Bangun *Optimizers* (SGD, Momentum, Adam) dengan perlindungan *gradient clipping*.
- [ ] Susun *Numerical Gradient Checker* (penentu kebohongan propagasi balik).
- [ ] Implementasikan `MLPIntentClassifier` dan `RuleBasedIntentClassifier` dengan disiplin set data terstratifikasi.

### ⚖️ Phase 4: Decision Mathematics (Aristocrat's Judgment)
*Merubah skor dari subsistem menjadi tindakan (action).*
- [ ] Susun `ThresholdPolicy` dengan pita ketidakpastian (`ASK_USER`).
- [ ] Susun `ExpectedUtility` untuk biaya asimetris (*false positive* vs *false negative*).
- [ ] Susun `RiskGuardrail` & `HybridPolicy` (jalur cepat + eskalasi LLM).

### 👁️ Phase 5: Mathematical Observability & Security
*Kemampuan melihat angka dan menjaga istana Ruka dari keruntuhan.*
- [ ] Bangun `MetricsRecorder` untuk metrik P50/P95.
- [ ] Terapkan redaksi rekursif (`redact`) untuk *Google API Keys* dan tipe *PII* (Token/Email) sebelum pencatatan masuk log.
- [ ] Refaktor `RukaSelfModel` agar 100% *queryable* dan tidak berhalusinasi kapabilitas.
- [ ] Integrasikan `ruka_cognition` ke dalam `ruka_app.py` & `cli.py` (`ruka-agent`).

---

## 🛠️ Aturan Eksekusi (Rules of Engagement)
- **Numpy Only:** Untuk pembelajaran, kita tidak akan mengimpor kerangka kerja besar seperti PyTorch/TensorFlow. Hanya NumPy `>1.26` yang diperlukan.
- **Test-Driven:** Tidak ada *layer* kognitif yang digabungkan sebelum `test_network_gradients.py` dan `test_similarity.py` lolos tanpa syarat.
- **Fail Fast:** `ModuleNotFoundError`, ketidakcocokan bentuk (*shape mismatch*), atau gradien *NaN* harus menyebabkan *crash* dini (*raise Error*), tidak boleh ditelan secara diam-diam.
