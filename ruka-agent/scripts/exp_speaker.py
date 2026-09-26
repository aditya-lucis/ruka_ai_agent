"""Experiment: Speaker verification FAR/FRR sweep and EER evaluation.

Reproduces Table 11.1 and results/speaker_eer.json in accordance with RUKA-IV.
Simulates 50 speakers with shared acoustic subspace and channel noise.
"""

from __future__ import annotations

import json
import os
import numpy as np

from ruka_perception.speaker.verification import (
    SpeakerVerifier,
    eer,
    far_frr_sweep,
    roc_points,
)


def run_experiment(seed: int = 42) -> dict:
    np.random.seed(seed)
    n_speakers = 50
    n_samples_per_speaker = 8
    dim = 64

    # Ruang suara bersama (shared subspace / base human voice timbre)
    shared_base = np.random.randn(dim)
    shared_base = shared_base / np.linalg.norm(shared_base)

    # Identitas pembicara: kombinasi basis bersama + deviasi unik
    speaker_bases = []
    for _ in range(n_speakers):
        unique = np.random.randn(dim) * 0.35
        v = shared_base + unique
        speaker_bases.append(v / np.linalg.norm(v))

    # Simulasi rekaman per pembicara dengan noise kanal
    recordings = {}
    channel_noise_scale = 0.28
    for s_idx, s_base in enumerate(speaker_bases):
        recs = []
        for _ in range(n_samples_per_speaker):
            noise = np.random.randn(dim) * channel_noise_scale
            r = s_base + noise
            recs.append(r / np.linalg.norm(r))
        recordings[f"speaker_{s_idx:02d}"] = np.array(recs)

    # Enrollment 4 rekaman pertama per pembicara
    enrolled = {}
    for name, recs in recordings.items():
        enrolled[name] = SpeakerVerifier.enroll(recs[:4])

    verifier = SpeakerVerifier(threshold=0.735)

    genuine_scores = []
    impostor_scores = []

    for name, recs in recordings.items():
        probe_genuine = recs[4:]
        for p in probe_genuine:
            genuine_scores.append(verifier.score(p, enrolled[name]))

        # Impostor: probe dari pembicara lain
        for other_name, other_recs in recordings.items():
            if other_name == name:
                continue
            impostor_scores.append(verifier.score(other_recs[4], enrolled[name]))

    # FAR / FRR sweep & EER
    sweep = far_frr_sweep(genuine_scores, impostor_scores, thresholds=np.linspace(0.4, 0.95, 201))
    eer_res = eer(sweep)
    roc = roc_points(sweep)

    gen_mean = float(np.mean(genuine_scores))
    gen_std = float(np.std(genuine_scores))
    imp_mean = float(np.mean(impostor_scores))
    imp_std = float(np.std(impostor_scores))
    d_prime = (gen_mean - imp_mean) / np.sqrt(0.5 * (gen_std ** 2 + imp_std ** 2))

    summary = {
        "n_speakers": n_speakers,
        "n_genuine": len(genuine_scores),
        "n_impostor": len(impostor_scores),
        "genuine_score_mean": round(gen_mean, 3),
        "genuine_score_std": round(gen_std, 3),
        "impostor_score_mean": round(imp_mean, 3),
        "impostor_score_std": round(imp_std, 3),
        "d_prime": round(float(d_prime), 3),
        "eer": round(eer_res["eer"], 3),
        "eer_threshold": round(eer_res["threshold"], 3),
    }

    os.makedirs("results", exist_ok=True)
    out_path = os.path.join("results", "speaker_eer.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)

    print("Experiment completed. Summary:")
    print(json.dumps(summary, indent=2))
    return summary


if __name__ == "__main__":
    run_experiment()
