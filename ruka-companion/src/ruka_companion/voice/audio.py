"""RUKA VI: Voice Audio Core — Device-free AudioBuffer, WavIO, AudioCore, MicrophoneSource.
Strictly follows RUKA-VI Chapter XI (Voice I).
"""

from __future__ import annotations

import io
import time
import wave
from dataclasses import dataclass
from typing import Any

import numpy as np

TARGET_FS = 16_000
FRAME_MS = 25
HOP_MS = 10


@dataclass
class AudioBuffer:
    """Satu segmen audio + metadata pengambilan."""

    samples: np.ndarray  # float32 mono, rentang [-1, 1]
    fs: int
    source: str = "unknown"  # 'mic' | 'file' | 'telegram' | 'synthetic'
    captured_at_ms: int = 0

    def __post_init__(self) -> None:
        s = np.asarray(self.samples)
        if s.ndim != 1:
            raise ValueError("AudioBuffer mono 1-D saja")
        self.samples = s.astype(np.float32)
        if self.fs <= 0:
            raise ValueError("fs > 0")

    @property
    def duration_s(self) -> float:
        return self.samples.size / self.fs

    @property
    def rms(self) -> float:
        """RMS ≈ energi kasar — dipakai VAD & indikator level."""
        if self.samples.size == 0:
            return 0.0
        return float(np.sqrt(np.mean(self.samples.astype(np.float64) ** 2)))


class WavIO:
    """WAV mono 16-bit PCM I/O via stdlib `wave` — TANPA dependensi eksternal.
    Dipakai: fixture eksperimen ASR, voice note Telegram, uji VAD.
    """

    @staticmethod
    def save(path: str, samples: np.ndarray, fs: int = TARGET_FS) -> None:
        s = np.asarray(samples, dtype=np.float32).ravel()
        pcm = np.clip(s, -1.0, 1.0)
        pcm16 = (pcm * 32767.0).astype(np.int16)
        with wave.open(path, "wb") as w:
            w.setnchannels(1)
            w.setsampwidth(2)
            w.setframerate(fs)
            w.writeframes(pcm16.tobytes())

    @staticmethod
    def load_bytes(data: bytes) -> AudioBuffer:
        """Parse WAV bytes → AudioBuffer (float32 mono). Stereo → rata kanal."""
        with wave.open(io.BytesIO(data), "rb") as w:
            n_ch = w.getnchannels()
            fs = w.getframerate()
            sampwidth = w.getsampwidth()
            raw = w.readframes(w.getnframes())

        if sampwidth != 2:
            raise ValueError(f"hanya PCM 16-bit didukung, dapat {sampwidth * 8}-bit")
        pcm = np.frombuffer(raw, dtype=np.int16).astype(np.float32) / 32768.0
        if n_ch > 1:
            pcm = pcm.reshape(-1, n_ch).mean(axis=1)
        return AudioBuffer(samples=pcm, fs=fs, source="file")

    @staticmethod
    def load(path: str) -> AudioBuffer:
        with open(path, "rb") as f:
            return WavIO.load_bytes(f.read())


class AudioCore:
    """Utilitas sinyal inti (device-free) — framing, normalisasi, resample.
    Semua deterministik dan diuji; dipakai VAD, speaker, ASR adapter.
    """

    @staticmethod
    def frame(
        samples: np.ndarray,
        fs: int = TARGET_FS,
        frame_ms: int = FRAME_MS,
        hop_ms: int = HOP_MS,
    ) -> np.ndarray:
        """Potong jadi matriks frame (n_frames × frame_len).
        Zero-pad ekor bila sisa < 1 frame — panjang keluaran konsisten.
        """
        s = np.asarray(samples, dtype=np.float32).ravel()
        frame_len = max(1, int(fs * frame_ms / 1000))
        hop = max(1, int(fs * hop_ms / 1000))
        if s.size < frame_len:
            s = np.pad(s, (0, frame_len - s.size))
        n_frames = 1 + (s.size - frame_len) // hop
        idx = np.arange(frame_len)[None, :] + hop * np.arange(n_frames)[:, None]
        return s[idx]  # n_frames × frame_len

    @staticmethod
    def normalize_peak(samples: np.ndarray, target: float = 0.7) -> np.ndarray:
        """Normalisasi puncak (bukan kompresor) — jaga silang perangkat mic."""
        s = np.asarray(samples, dtype=np.float32).ravel().copy()
        peak = float(np.max(np.abs(s))) if s.size else 0.0
        if peak < 1e-8:
            return s  # hening — jangan bagi nol
        return (s / peak) * target

    @staticmethod
    def resample_linear(
        samples: np.ndarray, fs_in: int, fs_out: int = TARGET_FS
    ) -> np.ndarray:
        """Resample interpolasi linear (cukup untuk 16k→16k no-op dan 48k→16k).
        Untuk produksi berkualitas: librosa/soxr — ditulis jujur di buku
        (kualitas vs dependensi); inti pipeline Ruka fs 16 kHz dari awal.
        """
        if fs_in == fs_out:
            return np.asarray(samples, dtype=np.float32).ravel()
        if fs_in <= 0 or fs_out <= 0:
            raise ValueError("fs > 0")
        s = np.asarray(samples, dtype=np.float64).ravel()
        n_out = int(round(s.size * fs_out / fs_in))
        if n_out == 0:
            return np.zeros(0, dtype=np.float32)
        t_out = np.arange(n_out) / fs_out
        t_in_pos = t_out * fs_in
        i0 = np.clip(np.floor(t_in_pos).astype(int), 0, s.size - 1)
        i1 = np.clip(i0 + 1, 0, s.size - 1)
        frac = np.clip(t_in_pos - i0, 0.0, 1.0)
        out = s[i0] * (1.0 - frac) + s[i1] * frac
        return out.astype(np.float32)


class MicrophoneSource:
    """Lapisan DEVICE (sounddevice) — import malas + laporan jujur."""

    @staticmethod
    def capability() -> dict[str, Any]:
        info: dict[str, Any] = {
            "layer": "device",
            "kind": "microphone",
            "available": False,
        }
        try:
            import sounddevice as sd  # type: ignore[import-untyped] # noqa: PLC0415

            info["sounddevice_version"] = getattr(sd, "__version__", "unknown")
            devs = sd.query_devices()
            input_devs = [d for d in devs if d.get("max_input_channels", 0) > 0]
            if not input_devs:
                info.update({"available": False, "reason": "no_input_devices", "device_count": 0})
            else:
                info.update({"available": True, "reason": "ok", "device_count": len(input_devs)})
        except Exception as exc:  # pragma: no cover
            info.update({"available": False, "reason": f"{type(exc).__name__}: {exc}", "device_count": 0})
        return info

    @staticmethod
    def record(duration_s: float, fs: int = TARGET_FS) -> AudioBuffer:
        import sounddevice as sd  # type: ignore[import-untyped] # noqa: PLC0415

        raw = sd.rec(int(duration_s * fs), samplerate=fs, channels=1, dtype="float32")
        sd.wait()
        return AudioBuffer(samples=raw.ravel(), fs=fs, source="mic", captured_at_ms=int(time.time() * 1000))
