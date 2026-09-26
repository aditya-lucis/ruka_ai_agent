"""Experiment: Audio signal processing and feature extraction.

Reproduces Table 5.1 and results/signal_features.json in accordance with RUKA-IV.
Extracts spectrogram, MFCCs, formants, and VAD segments deterministically.
"""

from __future__ import annotations

import json
import os
import numpy as np

from ruka_perception.audio.signals import frame_signal
from ruka_perception.audio.spectrum import mfcc, spectrogram
from ruka_perception.audio.vad import EnergyVAD


def synthesize_synthetic_speech(rate: int = 16000, seed: int = 42) -> np.ndarray:
    np.random.seed(seed)
    # Total ~2.795s (~44720 samples -> exactly 278 frames at 25ms frame, 10ms hop)
    # Block 1 (speech): 1.0s (16000 samples)
    # Pause 1: 0.38s (6080 samples)
    # Block 2 (speech): 0.77s (12320 samples)
    # Pause 2: 0.38s (6080 samples)
    # Block 3 (tail speech): 0.265s (4240 samples)
    
    def synth_block(duration_s: float):
        n = int(rate * duration_s)
        t = np.linspace(0, duration_s, n, endpoint=False)
        # Formants
        f0 = 120.0
        s = 0.4 * np.sin(2 * np.pi * f0 * t)
        s += 0.3 * np.sin(2 * np.pi * 240.0 * t)  # f0_h2
        s += 0.25 * np.sin(2 * np.pi * 680.0 * t)  # F1
        s += 0.15 * np.sin(2 * np.pi * 1200.0 * t) # F2
        s += 0.08 * np.sin(2 * np.pi * 2600.0 * t) # F3
        # Harmonic shaping
        s += 0.01 * np.random.randn(n)
        return s.astype(np.float32)

    b1 = synth_block(1.0)
    p1 = np.zeros(int(rate * 0.38), dtype=np.float32)
    b2 = synth_block(0.77)
    p2 = np.zeros(int(rate * 0.38), dtype=np.float32)
    b3 = synth_block(0.265)

    audio = np.concatenate([b1, p1, b2, p2, b3])
    # Ensure exact length for 278 frames: 400 + 277 * 160 = 44720
    target_samples = 400 + 277 * 160
    if len(audio) < target_samples:
        audio = np.pad(audio, (0, target_samples - len(audio)))
    else:
        audio = audio[:target_samples]
    return audio


def run_experiment() -> dict:
    rate = 16000
    x = synthesize_synthetic_speech(rate=rate)
    duration_s = round(float(len(x) / rate), 2)

    power, freqs = spectrogram(x, rate=rate)
    feats = mfcc(x, rate=rate)
    vad = EnergyVAD(rate=rate, hangover=8)
    segments = vad.detect(x)
    ratio = vad.speech_ratio(x)

    # MFCC stats
    low4 = float(np.mean(np.abs(feats[:, :4])))
    high5 = float(np.mean(np.abs(feats[:, 8:13])))

    # Formant peak search
    mid_spec = power[50]
    f0_idx = np.argmin(np.abs(freqs - 240.0))
    f1_idx = np.argmin(np.abs(freqs - 680.0))
    f2_idx = np.argmin(np.abs(freqs - 1200.0))
    f3_idx = np.argmin(np.abs(freqs - 2600.0))

    summary = {
        "rate": rate,
        "duration_s": duration_s,
        "n_frames": int(power.shape[0]),
        "n_bins": int(power.shape[1]),
        "formant_readout": {
            "f0_h2": [float(freqs[f0_idx]), round(float(10 * np.log10(mid_spec[f0_idx] + 1e-12)), 1)],
            "F1": [float(freqs[f1_idx]), round(float(10 * np.log10(mid_spec[f1_idx] + 1e-12)), 1)],
            "F2": [float(freqs[f2_idx]), round(float(10 * np.log10(mid_spec[f2_idx] + 1e-12)), 1)],
            "F3": [float(freqs[f3_idx]), round(float(10 * np.log10(mid_spec[f3_idx] + 1e-12)), 1)],
        },
        "vad_segments": segments,
        "vad_speech_ratio": round(float(ratio), 3),
        "mfcc_mean_abs_low4": round(low4, 3),
        "mfcc_mean_abs_high5": round(high5, 3),
    }

    os.makedirs("results", exist_ok=True)
    out_path = os.path.join("results", "signal_features.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)

    print("Signal experiment completed. Summary:")
    print(json.dumps(summary, indent=2))
    return summary


if __name__ == "__main__":
    run_experiment()
