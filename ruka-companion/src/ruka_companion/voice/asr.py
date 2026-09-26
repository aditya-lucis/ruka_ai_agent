"""RUKA VI: Whisper ASR Adapter — Local faster-whisper with measured latency.
Strictly follows RUKA-VI Chapter XI.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any, Iterable

import numpy as np

from .audio import AudioBuffer, TARGET_FS


@dataclass
class Transcription:
    text: str
    language: str
    duration_s: float
    segments: tuple[dict[str, Any], ...]
    latency_s: float
    model_id: str


class WhisperASR:
    """ASR adapter via faster-whisper — LOKAL, jujur, melacak latensi."""

    def __init__(
        self,
        model_size: str = "tiny",
        device: str = "cpu",
        compute_type: str = "int8",
    ) -> None:
        self.model_size = model_size
        self._model: Any = None
        self._init_args = {"device": device, "compute_type": compute_type}
        self._load_s: float | None = None

    def load(self) -> float:
        """Muat model (download pertama + init). Mengembalikan durasi load."""
        if self._model is not None:
            return self._load_s or 0.0
        from faster_whisper import WhisperModel  # noqa: PLC0415

        t0 = time.perf_counter()
        self._model = WhisperModel(self.model_size, **self._init_args)
        self._load_s = time.perf_counter() - t0
        return self._load_s

    @property
    def loaded(self) -> bool:
        return self._model is not None

    def transcribe(
        self,
        buffer: AudioBuffer,
        language: str = "id",
        beam_size: int = 5,
        vad_filter: bool = True,
        vad_parameters: dict[str, Any] | None = None,
    ) -> Transcription:
        """AudioBuffer → Transcription. Mengembalikan LATENSI TERUKUR.
        NOTE (RUNTIME-VERIFIED 2026-09-10, faster-whisper 1.2.1): nama kwarg
        yang benar adalah `vad_parameters` — BUKAN `vad_params`.
        """
        if self._model is None:
            raise RuntimeError("model belum dimuat — load() dahulu")
        if buffer.fs != TARGET_FS:
            raise ValueError(f"ASR butuh {TARGET_FS} Hz, dapat {buffer.fs}")
        t0 = time.perf_counter()
        segments, info = self._model.transcribe(
            buffer.samples,
            language=language,
            beam_size=beam_size,
            vad_filter=vad_filter,
            vad_parameters=vad_parameters or {},
        )
        segs = [
            {"start": float(s.start), "end": float(s.end), "text": s.text.strip()}
            for s in segments
        ]
        latency = time.perf_counter() - t0
        return Transcription(
            text=" ".join(s["text"] for s in segs).strip(),
            language=str(getattr(info, "language", language)),
            duration_s=buffer.duration_s,
            segments=tuple(segs),
            latency_s=latency,
            model_id=f"faster-whisper:{self.model_size}",
        )

    def transcribe_segments(
        self,
        samples: np.ndarray,
        segments_ms: Iterable[tuple[int, int]],
        language: str = "id",
    ) -> list[Transcription]:
        """Transkrip per segmen VAD — pintu privasi: hanya bagian bersuara."""
        out: list[Transcription] = []
        for start_ms, end_ms in segments_ms:
            a = int(start_ms / 1000 * TARGET_FS)
            b = int(end_ms / 1000 * TARGET_FS)
            chunk = np.asarray(samples, dtype=np.float32).ravel()[a:b]
            if chunk.size == 0:
                continue
            out.append(
                self.transcribe(
                    AudioBuffer(samples=chunk, fs=TARGET_FS, source="vad-segment"),
                    language=language,
                )
            )
        return out


def asr_capability() -> dict[str, Any]:
    """Mengembalikan kapabilitas ASR lokal (faster-whisper)."""
    try:
        import faster_whisper  # noqa: F401
        return {"available": True, "reason": "faster-whisper terpasang"}
    except ImportError:
        return {"available": False, "reason": "faster-whisper belum terpasang"}
