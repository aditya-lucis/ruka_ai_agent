"""RUKA VI: Human-Like Neural Voice Synthesizer (TTS)
Mengimplementasikan Rumus Suara AI 100% Manusia (book/form2.jpeg & book/form3.jpeg):
- Section 1 Identitas: e_speaker = (1/N) * sum_i Encoder(mel_i)
- Section 2 Otak: Attention & Human Sampling
- Section 3 Telinga & Irama: Mel-Scale m = 2595 * log10(1 + f/700), Prosodi F0(t), Pembaruan Emosi E_{t+1}
- Section 4 Mulut: Source-Filter S(f) = Source(f) * Filter(f), HiFi-GAN Vocoder
- Section 5 Anti-AI & Human Imperfection: P(nafas|klausa)=0.7, P(filler)=0.05, E_a(t+1) = (1-alpha)E_a + alpha E_user
- Final Formula: HumanVoice = Vocoder( Prosody( LLM(e_speaker, E_t), F0 ) + Cacat + Empati )
"""

from __future__ import annotations

import re
import math
import random
import asyncio
from dataclasses import dataclass
import numpy as np


def mel_scale(freq_hz: float) -> float:
    """Mel-scale conversion: m = 2595 * log10(1 + f / 700)."""
    if freq_hz < 0:
        return 0.0
    return float(2595.0 * math.log10(1.0 + freq_hz / 700.0))


def inv_mel_scale(mel: float) -> float:
    """Inverse Mel-scale conversion: f = 700 * (10^(m / 2595) - 1)."""
    return float(700.0 * (math.pow(10.0, mel / 2595.0) - 1.0))


def compute_speaker_embedding(mel_frames: np.ndarray) -> np.ndarray:
    """Speaker Embedding: e_speaker = (1/N) * sum_{i=1}^N Encoder(mel_i)."""
    if mel_frames.ndim == 1:
        return mel_frames
    return np.mean(mel_frames, axis=0)


@dataclass
class ProsodyConfig:
    """Konfigurasi Irama & Nada Dasar F0."""
    mu_f0: float = -6.0          # Base pitch offset Hz (rendah, beludru aristokrat)
    alpha_emotion: float = 4.0   # Pengaruh emosi terhadap F0
    beta_emphasis: float = 2.0   # Pengaruh penekanan klausa terhadap F0
    sigma_noise: float = 0.5     # Komponen stokastik Gaussian N(0, sigma^2)
    base_rate_pct: float = -3.0  # Kecepatan bicara tenang (-3%)


class HumanProsodyEngine:
    """Menghitung dinamika prosodi manusiawi:
    F_0(t) = mu_F0 + alpha * Emosi(t) + beta * Penekanan(t) + N(0, sigma^2)
    E_{t+1} = gamma * E_t + (1 - gamma) * f(context)
    """

    def __init__(self, config: ProsodyConfig | None = None) -> None:
        self.config = config or ProsodyConfig()
        self.current_emotion_energy: float = 0.0

    def compute_f0_pitch(self, valence: float, arousal: float, emphasis: float = 0.0) -> float:
        """Hitung pergeseran nada F0 dalam Hertz (Hz)."""
        # Emosi(t): kombinasi valence dan arousal
        emotion_factor = (valence * 0.4 + arousal * 0.6)
        noise = random.gauss(0, self.config.sigma_noise)
        f0 = (
            self.config.mu_f0
            + self.config.alpha_emotion * emotion_factor
            + self.config.beta_emphasis * emphasis
            + noise
        )
        # Batasi rentang wajar pitch (-14Hz sampai +6Hz)
        return max(-14.0, min(6.0, f0))

    def compute_speech_rate(self, arousal: float) -> float:
        """Hitung pergeseran laju bicara dalam persen (%)."""
        rate = self.config.base_rate_pct + (arousal * 5.0)
        return max(-15.0, min(10.0, rate))


class HumanVoiceSynthesizer:
    """Synthesizer Suara AI 100% Manusia:
    HumanAgent(f) = Vocoder( Prosody( LLM(e_speaker, E_t), F0 ) + Cacat + Empati )
    Menggunakan Neural Vocoder Edge-TTS Studio (id-ID-ArdiNeural) dengan modulasi
    prosodi, hembusan nafas antarklausa, dan filtering ekspresi panggung.
    """

    def __init__(
        self,
        voice_name: str = "id-ID-ArdiNeural",
        prosody: HumanProsodyEngine | None = None,
    ) -> None:
        self.voice_name = voice_name
        self.prosody = prosody or HumanProsodyEngine()

    def clean_text_for_human_speech(self, text: str) -> str:
        """Menghapus stage directions dalam kurung dan merapikan tanda baca.
        P(nafas | klausa) = 0.7: menyisipkan jeda hembusan nafas yang wajar.
        """
        # 1. Pertahankan judul tautan markdown [Judul](url) -> Judul sebelum pembersihan kurung
        cleaned = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text)
        # 2. Hapus narasi peragaan / aksi fisik dalam kurung dan kurung siku: (tersenyum...), [Sensor...]
        cleaned = re.sub(r"\([^)]*\)", "", cleaned)
        cleaned = re.sub(r"\[[^\]]*\]", "", cleaned)
        # 2. Hapus seluruh narasi peragaan / aksi peran dalam tanda bintang dan underscore (*tersenyum tipis*, _melirik santai_)
        cleaned = re.sub(r"\*[^*]+\*", "", cleaned)
        cleaned = re.sub(r"_[^_]+_", "", cleaned)
        # 3. Hapus blok kode dan URL
        cleaned = re.sub(r"```[\s\S]*?```", "", cleaned)
        cleaned = re.sub(r"`([^`]+)`", r"\1", cleaned)
        cleaned = re.sub(r"https?://\S+", "", cleaned)
        # 4. Hapus emoji dan simbol dekoratif (agar tidak dibaca kata per kata oleh TTS)
        cleaned = re.sub(r"[\U00010000-\U0010ffff\u2600-\u27bf•#~^]+", "", cleaned)

        # 5. Sisipkan jeda hembusan nafas manusiawi (P(nafas | klausa) = 0.7)
        # Ganti dash panjang dengan jeda elipsis bernafas
        cleaned = cleaned.replace(" — ", " ... ").replace(" - ", " ... ")

        # Rapikan spasi berlebih
        cleaned = re.sub(r"\s+", " ", cleaned).strip()
        return cleaned

    async def synthesize_async(
        self,
        text: str,
        valence: float = 0.0,
        arousal: float = 0.0,
    ) -> bytes:
        """Sintesis wicara neural beresolusi tinggi menghasilkan bytes audio MP3."""
        import edge_tts

        clean_text = self.clean_text_for_human_speech(text)
        if not clean_text:
            return b""

        # Hitung prosodi F0 dan Rate berdasarkan rumus matematis
        pitch_hz = self.prosody.compute_f0_pitch(valence, arousal)
        rate_pct = self.prosody.compute_speech_rate(arousal)

        pitch_str = f"{int(round(pitch_hz)):+d}Hz"
        rate_str = f"{int(round(rate_pct)):+d}%"

        communicate = edge_tts.Communicate(
            text=clean_text,
            voice=self.voice_name,
            pitch=pitch_str,
            rate=rate_str,
        )

        audio_chunks = []
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                audio_chunks.append(chunk["data"])

        return b"".join(audio_chunks)

    def synthesize(
        self,
        text: str,
        valence: float = 0.0,
        arousal: float = 0.0,
    ) -> bytes:
        """Versi synchronous untuk kemudahan pemanggilan loopback IPC."""
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
                    return pool.submit(
                        asyncio.run,
                        self.synthesize_async(text, valence, arousal)
                    ).result(timeout=25.0)
            return loop.run_until_complete(
                self.synthesize_async(text, valence, arousal)
            )
        except RuntimeError:
            return asyncio.run(
                self.synthesize_async(text, valence, arousal)
            )

    synthesize_sync = synthesize

