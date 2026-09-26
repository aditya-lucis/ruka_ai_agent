"""RUKA VI: Voice Activity Detection (VAD).
Gerbang privasi sekaligus penghemat latensi.
Strictly follows RUKA-VI Chapter XI.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import numpy as np

from .audio import AudioCore, FRAME_MS, HOP_MS, TARGET_FS


@dataclass
class VADConfig:
    frame_ms: int = FRAME_MS
    hop_ms: int = HOP_MS
    noise_floor_init: float = 0.01
    speech_threshold_ratio: float = 2.4
    zcr_max: float = 0.35
    adaptation_rate: float = 0.05
    min_speech_ms: int = 120
    max_hangover_ms: int = 200


@dataclass
class VADResult:
    segments_ms: list[tuple[int, int]]
    speech_ratio: float
    noise_floor_final: float
    n_frames: int


def segment_ms(
    voiced: np.ndarray, hop_ms: int, min_speech_ms: int, hangover_ms: int
) -> list[tuple[int, int]]:
    """Kompresi boolean frame → segmen [start_ms, end_ms] + hangover ekor."""
    segs: list[tuple[int, int]] = []
    hangover_frames = max(1, int(round(hangover_ms / hop_ms)))
    min_frames = max(1, int(round(min_speech_ms / hop_ms)))
    i = 0
    n = voiced.size
    while i < n:
        if voiced[i]:
            j = i
            while j < n and voiced[j]:
                j += 1
            # hangover: perpanjang ke segmen bila ada suara lagi dalam window
            k = j
            while k < n and k - j <= hangover_frames:
                if voiced[k]:
                    while k < n and voiced[k]:
                        k += 1
                    j = k
                k += 1
            if (j - i) >= min_frames:
                segs.append((i * hop_ms, j * hop_ms))
            i = j
        else:
            i += 1
    return segs


class EnergyVAD:
    """VAD tiga kriteria: RMS adaptif, ZCR, dan minimum durasi."""

    def __init__(self, cfg: VADConfig | None = None) -> None:
        self.cfg = cfg or VADConfig()

    @staticmethod
    def _zcr(frame: np.ndarray) -> float:
        if frame.size < 2:
            return 0.0
        signs = np.sign(frame)
        signs[signs == 0] = 1
        return float(np.mean(np.abs(np.diff(signs)) > 0))

    def detect(self, samples: np.ndarray, fs: int = TARGET_FS) -> VADResult:
        cfg = self.cfg
        frames = AudioCore.frame(samples, fs, cfg.frame_ms, cfg.hop_ms)
        n = frames.shape[0]
        if n == 0:
            return VADResult([], 0.0, cfg.noise_floor_init, 0)
        rms = np.sqrt((frames.astype(np.float64) ** 2).mean(axis=1))
        zcr = np.array([self._zcr(f) for f in frames])
        noise_floor = float(cfg.noise_floor_init)
        voiced = np.zeros(n, dtype=bool)
        for i in range(n):
            is_candidate = (
                rms[i] >= cfg.speech_threshold_ratio * noise_floor
                and rms[i] > 1e-5
                and zcr[i] <= cfg.zcr_max
            )
            voiced[i] = is_candidate
            # lantai noise mengejar frame SENYAP lambat (adaptasi)
            if not is_candidate:
                noise_floor += cfg.adaptation_rate * (rms[i] - noise_floor)
                noise_floor = max(noise_floor, 1e-5)
        hop_ms_i = cfg.hop_ms
        segs = segment_ms(voiced, hop_ms_i, cfg.min_speech_ms, cfg.max_hangover_ms)
        speech_frames = int(np.sum(voiced))
        return VADResult(
            segments_ms=segs,
            speech_ratio=speech_frames / n,
            noise_floor_final=noise_floor,
            n_frames=n,
        )
