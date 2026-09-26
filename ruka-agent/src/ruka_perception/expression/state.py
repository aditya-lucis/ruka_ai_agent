"""Expression State — matematika kondisi interaksi Ruka.

TIGA LAPIS yang TIDAK BOLEH dicampur (Vol IV Part XII):
  1. EMOTION (biologis)        : milik organisme — RUKA TIDAK
     PUNYA dan TIDAK DIKLAIM PUNYA.
  2. INTERACTION STATE         : vektor kondisi internal S yang
     berevolusi oleh transisi matematis. Status UI yang jujur.
  3. EXPRESSION POLICY         : peta S -> ekspresi eksternal
     (teks/suara/avatar) dengan batas kejujuran.

Model transisi (bagian inti):
    S(t+1) = alpha * S(t) + (1 - alpha) * baseline + beta * C(t) + gamma * E(t)
    S : state sebelumnya (5 dimensi)
    C : context signal (sinyal konteks dari persepsi/appraisal)
    E : interaction event (event eksplisit: pujian, kritik, error)
alpha = retention (decay ke arah baseline), beta = sensitivitas
konteks, gamma = dampak event. Semua komponen di-clamp [0, 1].

Implements Listing 12.4 from RUKA-IV.
"""

from __future__ import annotations

import numpy as np

# Dimensi state — urutan tetap, ini KONTRAK lintas modul.
STATE_DIMS = ["calm", "curiosity", "concern", "playfulness", "confidence"]


class ExpressionState:
    """State vector + mesin transisi. Deterministik & tanpa side effect global.

    Semua parameter eksplisit di konstruktor.
    """

    def __init__(
        self,
        alpha: float = 0.90,
        beta: float = 0.10,
        gamma: float = 0.35,
        baseline: np.ndarray | None = None,
        max_delta: float = 0.25,
        update_gain: float = 1.0,
    ) -> None:
        if not (0 <= alpha <= 1 and 0 <= beta <= 1 and 0 <= gamma <= 1):
            raise ValueError("alpha, beta, gamma di [0, 1]")
        if not (0 < max_delta <= 1):
            raise ValueError("max_delta di (0, 1]")
        self.alpha = alpha
        self.beta = beta
        self.gamma = gamma
        self.max_delta = max_delta
        self.update_gain = update_gain
        if baseline is None:
            # baseline default: tenang + percaya diri sedang
            baseline = np.array([0.85, 0.30, 0.10, 0.25, 0.60])
        self.baseline = np.asarray(baseline, dtype=np.float64)
        if self.baseline.shape != (len(STATE_DIMS),):
            raise ValueError(f"baseline harus ({len(STATE_DIMS)},)")
        self.s = self.baseline.copy()
        self.history: list[np.ndarray] = [self.s.copy()]

    # ----------------------------------------------------------------

    def step(
        self,
        context: np.ndarray | None = None,
        event: np.ndarray | None = None,
    ) -> np.ndarray:
        """Satu transisi waktu. Return state baru (copy).

        Histeresis: perubahan per langkah dibatasi max_delta —
        Ruka tidak melompat dari calm ke panik dalam satu pesan.
        Baru setelah 2-3 langkah sinyal konsisten arahnya state
        sampai ke sana. Anti-osilasi: update_gain < 1 meredam.
        """
        c = (
            np.zeros(len(STATE_DIMS))
            if context is None
            else np.asarray(context, dtype=np.float64)
        )
        e = (
            np.zeros(len(STATE_DIMS))
            if event is None
            else np.asarray(event, dtype=np.float64)
        )
        for vec, name in ((c, "context"), (e, "event")):
            if vec.shape != (len(STATE_DIMS),):
                raise ValueError(f"{name} harus ({len(STATE_DIMS)},)")
        # decay ke baseline + injeksi sinyal
        target = (
            self.alpha * self.s
            + (1 - self.alpha) * self.baseline
            + self.beta * c
            + self.gamma * e
        )
        # histeresis: batasi perubahan per langkah
        delta = np.clip(target - self.s, -self.max_delta, self.max_delta)
        nxt = np.clip(self.s + self.update_gain * delta, 0.0, 1.0)
        self.s = nxt
        self.history.append(self.s.copy())
        return self.s.copy()

    # ----------------------------------------------------------------

    def dominant(self) -> str:
        """Dimensi dominan (setelah dikurangi baseline — yang menonjol
        RELATIF terhadap kebiasaan, bukan absolut).
        """
        rel = self.s - self.baseline
        return STATE_DIMS[int(np.argmax(rel))]

    def to_avatar_label(self) -> str:
        """Peta state -> kosakata ekspresi avatar diskrit (Part XIII).

        Ambil dominan relatif + gerbang minimum supaya tidak menari
        setiap pesan.
        """
        rel = self.s - self.baseline
        i = int(np.argmax(rel))
        # hanya ganti ekspresi bila deviasi cukup berarti
        if rel[i] < 0.08:
            return "neutral"
        return {
            "calm": "calm",
            "curiosity": "curious",
            "concern": "concerned",
            "playfulness": "playful",
            "confidence": "proud",
        }[STATE_DIMS[i]]

    # ----------------------------------------------------------------

    def stability_report(self, window: int = 8) -> dict:
        """Diagnosa stabilitas — dipakai test & observability.

        osc_rate : frekuensi ARAH perubahan terbesar berganti tanda
                   (osilasi = bolak-balik, bukan sekadar ganti label)
        mean_jump: rata-rata |delta| per langkah (kegembiraan liar)
        settled  : sudah dekat baseline (percakapan tenang)
        """
        h = np.array(self.history)
        if len(h) < 2:
            return {"osc_rate": 0.0, "mean_jump": 0.0, "settled": True}
        w = min(window, len(h) - 1)
        recent = h[-(w + 1):]
        deltas = np.diff(recent, axis=0)  # (w, 5)
        # langkah dengan perubahan berarti saja yang dihitung
        signs, mag = [], []
        for d in deltas:
            j = int(np.argmax(np.abs(d)))
            m = float(d[j])
            mag.append(abs(m))
            if abs(m) > 0.01:
                signs.append(1 if m > 0 else -1)
        flips = sum(1 for a, b in zip(signs, signs[1:]) if a != b)
        osc = flips / max(len(signs) - 1, 1) if len(signs) > 1 else 0.0
        dist = np.linalg.norm(self.s - self.baseline)
        return {
            "osc_rate": float(osc),
            "mean_jump": float(np.mean(mag)) if mag else 0.0,
            "settled": bool(dist < 0.12),
        }
