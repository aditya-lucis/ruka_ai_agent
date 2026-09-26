"""RUKA VI: Speaker Recognition — MFCC from first principles, Gaussian profile, and LLR verification.
Strictly follows RUKA-VI Chapter XII (Voice II).
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any

import numpy as np

from ..math.metrics import threshold_report
from .audio import AudioCore


def mfcc(
    samples: np.ndarray,
    fs: int = 16_000,
    n_mfcc: int = 20,
    n_filters: int = 26,
    n_fft: int = 512,
    fmin: float = 60.0,
    fmax: float | None = None,
) -> np.ndarray:
    """MFCC (Kontinuitas Vol IV): frame → window → |FFT|² → mel → log → DCT.
    → (n_frames × n_mfcc). Implementasi NumPy murni — deterministik.
    """
    s = np.asarray(samples, dtype=np.float64).ravel()
    if s.size < n_fft:
        s = np.pad(s, (0, n_fft - s.size))
    frames = AudioCore.frame(s.astype(np.float32), fs).astype(np.float64)
    frames = frames[: frames.shape[0] - 1] if frames.shape[0] > 1 else frames

    # window Hann
    win = np.hanning(frames.shape[1])
    spec = np.abs(np.fft.rfft(frames * win[None, :], n=n_fft, axis=1)) ** 2

    # mel filterbank
    fmax = fmax if fmax is not None else fs / 2.0
    mel = lambda f: 2595.0 * np.log10(1.0 + f / 700.0)
    inv_mel = lambda m: 700.0 * (10.0 ** (m / 2595.0) - 1.0)
    m_pts = np.linspace(mel(fmin), mel(fmax), n_filters + 2)
    f_pts = inv_mel(m_pts)
    bins = np.floor((n_fft + 1) * f_pts / fs).astype(int)
    fbank = np.zeros((n_filters, spec.shape[1]))
    for j in range(n_filters):
        b0, b1, b2 = bins[j], bins[j + 1], bins[j + 2]
        if b1 <= b0 or b2 <= b1:
            continue
        for k in range(b0, b1):
            if 0 <= k < fbank.shape[1]:
                fbank[j, k] = (k - b0) / (b1 - b0)
        for k in range(b1, b2):
            if 0 <= k < fbank.shape[1]:
                fbank[j, k] = (b2 - k) / (b2 - b1)
    energy = spec @ fbank.T
    energy = np.log(np.clip(energy, 1e-10, None))

    # DCT-II (ortogonal)
    n = energy.shape[1]
    k = np.arange(n_mfcc)[:, None]
    m = np.arange(n)[None, :]
    dct = np.cos(np.pi * k * (m + 0.5) / n) * np.sqrt(2.0 / n)
    feats = energy @ dct.T
    return feats  # n_frames × n_mfcc


@dataclass
class SpeakerProfile:
    """Profil pembicara: statistik Gaussian atas fitur MFCC."""

    profile_id: str
    mean: np.ndarray
    cov_diag: np.ndarray
    n_frames: int
    created_at_ms: int = 0
    variance_floor: float = 1e-4

    def logpdf_frame_mean(self, feats: np.ndarray) -> float:
        """(1/T) sum_t log N(f_t; mu, diag(sigma^2))"""
        var = np.maximum(self.cov_diag, self.variance_floor)
        log_2pi_var = np.log(2.0 * np.pi * var)
        diff = feats - self.mean[None, :]
        quad = (diff**2) / var[None, :]
        log_probs = -0.5 * np.sum(log_2pi_var[None, :] + quad, axis=1)
        return float(np.mean(log_probs))

    def as_dict(self) -> dict[str, Any]:
        return {
            "profile_id": self.profile_id,
            "mean": self.mean.tolist(),
            "cov_diag": self.cov_diag.tolist(),
            "n_frames": self.n_frames,
            "created_at_ms": self.created_at_ms,
            "variance_floor": self.variance_floor,
        }

    @staticmethod
    def from_dict(d: dict[str, Any]) -> SpeakerProfile:
        return SpeakerProfile(
            profile_id=d["profile_id"],
            mean=np.asarray(d["mean"], dtype=np.float64),
            cov_diag=np.asarray(d["cov_diag"], dtype=np.float64),
            n_frames=int(d["n_frames"]),
            created_at_ms=int(d.get("created_at_ms", 0)),
            variance_floor=float(d.get("variance_floor", 1e-4)),
        )


@dataclass(frozen=True)
class EnrollmentQuality:
    score: float
    n_frames: int
    note: str


class AcousticGaussianProvider:
    """Provider A: MFCC + Gaussian per-pembicara (Lokal, verifiable)."""

    provider_id: str = "acoustic-llr-v1"

    def __init__(self, threshold: float = 1.0, min_enroll_frames: int = 40):
        self.threshold = threshold
        self.min_enroll_frames = min_enroll_frames
        self.profiles: dict[str, SpeakerProfile] = {}

    def enroll(
        self, profile_id: str, samples: np.ndarray, fs: int = 16_000
    ) -> SpeakerProfile:
        feats = mfcc(samples, fs)
        if feats.shape[0] < self.min_enroll_frames:
            raise ValueError(
                f"enrollment butuh ≥{self.min_enroll_frames} frame, dapat {feats.shape[0]}"
            )
        mean = feats.mean(axis=0)
        cov = feats.var(axis=0)
        profile = SpeakerProfile(
            profile_id=profile_id,
            mean=mean,
            cov_diag=cov,
            n_frames=int(feats.shape[0]),
            created_at_ms=int(time.time() * 1000),
        )
        self.profiles[profile_id] = profile
        return profile

    def enrollment_quality(self, profile_id: str) -> EnrollmentQuality:
        p = self.profiles.get(profile_id)
        if p is None:
            raise KeyError(profile_id)
        dur_s = p.n_frames * 0.01  # hop 10 ms
        dur_score = min(1.0, dur_s / 8.0)
        var_score = float(
            np.clip(np.mean(np.sqrt(np.maximum(p.cov_diag, 0))) / 6.0, 0.0, 1.0)
        )
        score = 0.6 * dur_score + 0.4 * var_score
        note = (
            f"durasi≈{dur_s:.1f}s, variasi-fitur ok"
            if score > 0.5
            else "enrollment pendek/monoton — tambah sampel bervariasi"
        )
        return EnrollmentQuality(score=round(score, 3), n_frames=p.n_frames, note=note)

    def _world_model(self, exclude_id: str) -> SpeakerProfile:
        others = [p for pid, p in self.profiles.items() if pid != exclude_id]
        if others:
            mean = np.mean([p.mean for p in others], axis=0)
            cov = np.mean([p.cov_diag for p in others], axis=0)
            n = sum(p.n_frames for p in others)
            return SpeakerProfile("_world", mean, cov, n, 0)
        p = self.profiles[exclude_id]
        return SpeakerProfile("_world", p.mean, p.cov_diag * 2.0, p.n_frames, 0)

    def verify(
        self, samples: np.ndarray, claimed_id: str, fs: int = 16_000
    ) -> tuple[float, str]:
        if claimed_id not in self.profiles:
            return 0.0, "NO_PROFILE"
        feats = mfcc(samples, fs)
        if feats.shape[0] == 0:
            return 0.0, "REJECT"
        claimed = self.profiles[claimed_id]
        world = self._world_model(claimed_id)
        ll_claimed = claimed.logpdf_frame_mean(feats)
        ll_world = world.logpdf_frame_mean(feats)
        llr = ll_claimed - ll_world
        verdict = "ACCEPT" if llr >= self.threshold else "REJECT"
        return float(llr), verdict

    def identify(
        self, samples: np.ndarray, fs: int = 16_000
    ) -> tuple[str | None, float]:
        best_id, best_llr = None, float("-inf")
        for pid in sorted(self.profiles):
            llr, _ = self.verify(samples, pid, fs)
            if llr > best_llr:
                best_llr, best_id = llr, pid
        return best_id, float(best_llr)

    def calibrate(
        self,
        genuine: dict[str, list[np.ndarray]],
        impostor_pairs: list[tuple[str, np.ndarray]],
    ) -> dict[str, Any]:
        g_scores: list[float] = []
        for pid, chunks in genuine.items():
            for c in chunks:
                llr, _v = self.verify(c, pid)
                g_scores.append(llr)
        i_scores: list[float] = []
        for claimed, c in impostor_pairs:
            llr, _v = self.verify(c, claimed)
            i_scores.append(llr)
        if not g_scores or not i_scores:
            raise ValueError("kalibrasi butuh skor genuine DAN impostor")
        rep = threshold_report(g_scores, i_scores, c_fa=10.0, c_miss=1.0)
        self.threshold = rep["eer_threshold"]
        rep["provider"] = self.provider_id
        rep["label"] = "MEASURED-SYNTHETIC bila data sintetis (bukan dataset suara nyata)"
        return rep

    def capability(self) -> dict[str, Any]:
        return {
            "provider": self.provider_id,
            "layer": "perception",
            "kind": "speaker-recognition",
            "available": True,
            "n_profiles": len(self.profiles),
            "threshold": self.threshold,
            "honesty": (
                "acoustic Gaussian MFCC — akurasi TERBATAS; jangan "
                "dipakai sebagai satu-satunya autentikasi aksi berbahaya"
            ),
        }


class ExternalDVectorProvider:
    """Provider B: d-vector eksternal — UNVERIFIED STUB JUJUR."""

    provider_id: str = "external-dvector-UNVERIFIED"

    def __init__(self) -> None:
        self._embed_fn: Any = None

    def bind_embed_function(self, fn: Any) -> None:
        if not callable(fn):
            raise ValueError("butuh callable embed")
        self._embed_fn = fn

    def embed(self, samples: np.ndarray, fs: int = 16_000) -> np.ndarray:
        if self._embed_fn is None:
            raise RuntimeError("provider d-vector eksternal belum diikat (UNVERIFIED)")
        return np.asarray(self._embed_fn(samples, fs))

    def capability(self) -> dict[str, Any]:
        return {
            "provider": self.provider_id,
            "layer": "perception",
            "kind": "speaker-dvector",
            "available": self._embed_fn is not None,
            "status": "bound" if self._embed_fn is not None else "unverified_stub",
            "honesty": "unverified external d-vector stub — requires explicit binding",
        }
