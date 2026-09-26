"""Energy-based Voice Activity Detection with hysteresis for Ruka Perception.

Implements Listing 5.4 from RUKA-IV.
Features dual-threshold hysteresis, hangover margin, dynamic range guard,
and noise floor calibration to prevent audio hallucination or chopping speech.
"""

from __future__ import annotations

import numpy as np
from .signals import frame_signal, to_db


def frame_features(
    x: np.ndarray,
    rate: int = 16000,
    frame_ms: float = 25.0,
    hop_ms: float = 10.0,
) -> tuple[np.ndarray, np.ndarray]:
    """Ekstraksi energi frame dalam dB dan Zero Crossing Rate (ZCR).

    Return:
        energy_db : (n_frames,) tingkat energi RMS dalam dB
        zcr       : (n_frames,) laju pergantian tanda gelombang
    """
    frames = frame_signal(x, frame_ms=frame_ms, hop_ms=hop_ms, rate=rate)
    # RMS per frame
    rms_vals = np.sqrt(np.mean(np.square(frames.astype(np.float64)), axis=1))
    energy_db = to_db(rms_vals, floor_db=-80.0, reference=1.0)
    
    # Zero Crossing Rate (ZCR)
    signs = np.signbit(frames)
    zcr = np.mean(np.abs(np.diff(signs, axis=1)), axis=1).astype(np.float64)
    return energy_db, zcr


class EnergyVAD:
    """Voice Activity Detector berbasis energi dengan histeresis.

    Menggunakan dua ambang (ON lebih tinggi dari OFF) dan hangover buffer
    untuk menjaga keutuhan jeda alami dalam ucapan manusia.
    """

    def __init__(
        self,
        rate: int = 16000,
        frame_ms: float = 25.0,
        hop_ms: float = 10.0,
        noise_floor_db: float = -50.0,
        min_dynamic_db: float = 6.0,
        on_offset_db: float = -15.0,
        off_offset_db: float = -25.0,
        hangover: int = 8,
        min_segment_ms: float = 50.0,
        min_speech_frames: int = 3,
    ) -> None:
        self.rate = rate
        self.frame_ms = frame_ms
        self.hop_ms = hop_ms
        self.noise_floor_db = noise_floor_db
        self.min_dynamic_db = min_dynamic_db
        self.on_offset_db = on_offset_db
        self.off_offset_db = off_offset_db
        self.hangover = hangover
        self.min_segment_ms = min_segment_ms
        self.min_speech_frames = min_speech_frames

    def detect(self, x: np.ndarray) -> list[tuple[int, int]]:
        """Segmen ucapan [(i_start, i_end_frame), ...] dengan histeresis.

        Aturan transisi:
          OFF->ON  : energi >= on_threshold  (dan segmen berikut cukup
                     panjang — filter min_speech_frames saat menutup)
          ON->OFF  : energi < off_threshold SELAMA hangover frames
                     berturut-turut. Satu frame bising tak menutup
                     segmen; jeda panjang menutup.
        Segmen lebih pendek dari min_segment_ms dibuang sebagai klik.
        """
        energy_db, _zcr = frame_features(
            x, self.rate, self.frame_ms, self.hop_ms
        )
        ref = float(np.percentile(energy_db, 90))
        ref = max(ref, self.noise_floor_db)
        dynamic = ref - float(np.percentile(energy_db, 10))
        if dynamic < self.min_dynamic_db:
            return []  # sinyal datar: bukan ucapan

        on_thr = ref + self.on_offset_db
        off_thr = ref + self.off_offset_db
        n = len(energy_db)
        segments: list[tuple[int, int]] = []
        in_speech = False
        start = 0
        quiet_run = 0

        for i, e in enumerate(energy_db):
            if not in_speech:
                if e >= on_thr:
                    in_speech = True
                    start = i
                    quiet_run = 0
            else:
                if e < off_thr:
                    quiet_run += 1
                    if quiet_run >= self.hangover:
                        self._close(segments, start, i - quiet_run + 1)
                        in_speech = False
                        quiet_run = 0
                else:
                    quiet_run = 0

        if in_speech:
            self._close(segments, start, n)

        # segmen terlalu pendek = klik/bising -> buang
        min_frames = max(1, int(self.min_segment_ms / self.hop_ms))
        return [(a, b) for a, b in segments if (b - a) >= min_frames]

    def _close(self, segments: list[tuple[int, int]], start: int, end: int) -> None:
        """Tutup segmen pada frame 'end' (frame pertama yang hening).

        Panjang validasi min_speech_frames diterapkan di sini.
        """
        if end - start >= self.min_speech_frames:
            segments.append((start, end))

    def speech_ratio(self, x: np.ndarray) -> float:
        """Porsi durasi terdeteksi sebagai ucapan — metrik kesehatan input audio.

        (Audio 30 detik tanpa ucapan = salah file / salah tombol, jangan dikirim ke ASR).
        """
        segments = self.detect(x)
        frame_len = int(self.rate * self.frame_ms / 1000.0)
        hop_len = int(self.rate * self.hop_ms / 1000.0)
        if len(x) < frame_len:
            return 0.0
        frames = 1 + (len(x) - frame_len) // hop_len
        if frames <= 0:
            return 0.0
        speech_frames = sum(end - start for start, end in segments)
        return float(speech_frames / frames)
