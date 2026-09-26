"""Matematika kepentingan memori — I(m) (Part VI).
I(m) = w_r*Recency + w_f*Frequency + w_e*Emotional + w_t*Task + w_u*UserImportance
Setiap variabel dijelaskan, dinormalisasi ke [0,1], dan punya mode gagal
yang didokumentasikan — rumus ini alat keputusan, bukan hiasan.
ASUMSI (jujur, bisa dibantah):
  1. Kelima sumber kepentingan layak dijumlah linier. Linier = mudah
     diaudit, mudah dibantah; non-linier (perkalian gating) bisa
     ditambah bila eksperimen menunjukkan kebutuhan.
  2. Bobot default TIDAK suci: ia titik awal dari pengukuran, bukan
     wahyu. Fungsi kalibrasi bobot disediakan (fit_weights).
  3. Emotional relevance bukan 'perasaan Ruka' — ia skor appraisal
     warisan Vol IV (seberapa kuat kejadian mempengaruhi interaksi).
  4. Recency memakai peluruhan eksponensial dengan half-life,
     bukan pembagian usia polos: R = 2^(-umur_hari / h).
  5. Frequency jenuh secara logaritmik: 100 kejadian tidak 100x
     lebih penting dari 1 kejadian.
"""
from __future__ import annotations
import math
from dataclasses import dataclass, field

DEFAULT_WEIGHTS = {
    "recency": 0.25,
    "frequency": 0.25,
    "emotional": 0.15,
    "task": 0.20,
    "user": 0.15,
}

# Half-life (hari) per kelas memori: episodik harian cepat pudar,
# fakta identitas Bos nyaris abadi. Ini TUNABLE, bukan konstanta alam.
DEFAULT_HALF_LIFE_DAYS = {
    "working": 0.25,
    "short_term": 2.0,
    "episodic": 30.0,
    "semantic": 365.0,
    "preference": 180.0,
    "relationship": 365.0,
}

class ImportanceScorer:
    """Mesin penilai I(m) dengan bobot terkalibrasi dan batas bawah."""
    
    def __init__(self, weights: dict[str, float] | None = None):
        self.weights = dict(DEFAULT_WEIGHTS)
        if weights:
            self.weights.update(weights)
        
        # Validasi jumlah bobot harus 1.0
        total = sum(self.weights.values())
        if not math.isclose(total, 1.0, abs_tol=1e-9):
            raise ValueError(f"Bobot I(m) harus berjumlah 1.0, saat ini {total:.4f}")

    def score(self, 
              age_days: float = 0.0,
              frequency: int = 1,
              emotional: float = 0.0,
              task_relevance: float = 0.0,
              user_importance: float = 0.0,
              memory_kind: str = "episodic") -> float:
        """Menghitung I(m) berdasarkan 5 pilar."""
        
        # 1. Recency
        hl = DEFAULT_HALF_LIFE_DAYS.get(memory_kind, 30.0)
        recency_score = 2.0 ** (-age_days / hl) if age_days >= 0 else 1.0

        # 2. Frequency (Jenuh logaritmik, S=20 -> ~0.87)
        S = 20.0
        freq_score = math.log(1 + frequency) / math.log(1 + S)
        freq_score = min(1.0, freq_score)

        # 3. Emotional
        emo_score = min(1.0, max(0.0, emotional))

        # 4. Task
        task_score = min(1.0, max(0.0, task_relevance))

        # 5. User
        user_score = min(1.0, max(0.0, user_importance))

        # Kalkulasi akhir (linier fusion)
        final_score = (
            self.weights["recency"] * recency_score +
            self.weights["frequency"] * freq_score +
            self.weights["emotional"] * emo_score +
            self.weights["task"] * task_score +
            self.weights["user"] * user_score
        )
        
        return round(final_score, 6)
