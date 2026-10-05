# -*- coding: utf-8 -*-
"""Presence Observability Ring Buffer & 64-bit Perceptual Hash (FR-PR-11, FR-PR-12).

Observabilitas performa loop kehadiran:
- Ring buffer 18.000 frame metadata-saja (tanpa muatan media, overhead < 0.5% CPU)
- Uji golden frame berbasis perceptual hash 64-bit (Hamming distance > 10 = regresi visual)
"""
from __future__ import annotations

import collections
import time
from typing import Any, Optional
from src.presence.models import PresenceFrame


class PresenceRingBuffer:
    """Ring buffer 18.000 frame berisi metadata saja (FR-PR-11)."""

    def __init__(self, capacity: int = 18000) -> None:
        self.capacity = capacity
        # Menyimpan tuple ringkas: (frame_index, timestamp, frame_duration_ms, mood, degradation)
        self.buffer: collections.deque[tuple[int, float, float, str, str]] = collections.deque(maxlen=capacity)

    def record(self, frame: PresenceFrame, frame_duration_ms: float) -> None:
        self.buffer.append(
            (
                frame.frame_index,
                frame.timestamp,
                round(frame_duration_ms, 3),
                frame.mood.value,
                frame.degradation.value,
            )
        )

    def size(self) -> int:
        return len(self.buffer)

    def calculate_p95_latency(self, last_n_frames: int = 300) -> float:
        """Menghitung p95 durasi frame dari N frame terakhir."""
        if not self.buffer:
            return 0.0
        n = min(len(self.buffer), last_n_frames)
        sample = [self.buffer[-i][2] for i in range(1, n + 1)]
        sample.sort()
        p95_idx = int(math.ceil(0.95 * len(sample))) - 1
        return sample[max(0, p95_idx)]


import math


def compute_frame_phash_64(frame: PresenceFrame) -> int:
    """Menghasilkan perceptual hash 64-bit deterministik dari pose frame (FR-PR-12).

    Mengkuantisasi 8 fitur kunci masing-masing menjadi 8 bit:
    1. chest_scale (normalisasi 1.0 - 1.05)
    2. blink_left (0.0 - 1.0)
    3. ear_left_angle (-30 - 45)
    4. ear_right_angle (-30 - 45)
    5. tail_segment_tip (-45 - 45)
    6. head_yaw (-75 - 75)
    7. eye_look_x (-1.0 - 1.0)
    8. eye_look_y (-1.0 - 1.0)
    """
    def _quantize_8bit(val: float, min_val: float, max_val: float) -> int:
        norm = (val - min_val) / max(1e-5, (max_val - min_val))
        clamped = max(0.0, min(1.0, norm))
        return int(clamped * 255)

    b1 = _quantize_8bit(frame.breathing.chest_scale, 1.0, 1.05)
    b2 = _quantize_8bit(frame.blink_left, 0.0, 1.0)
    b3 = _quantize_8bit(frame.ear.left_angle_deg, -30.0, 45.0)
    b4 = _quantize_8bit(frame.ear.right_angle_deg, -30.0, 45.0)
    b5 = _quantize_8bit(frame.tail.segments_deg[4], -45.0, 45.0)
    b6 = _quantize_8bit(frame.head_yaw_deg, -75.0, 75.0)
    b7 = _quantize_8bit(frame.eye_look_x, -1.0, 1.0)
    b8 = _quantize_8bit(frame.eye_look_y, -1.0, 1.0)

    phash = (
        (b1 << 56)
        | (b2 << 48)
        | (b3 << 40)
        | (b4 << 32)
        | (b5 << 24)
        | (b6 << 16)
        | (b7 << 8)
        | b8
    )
    return phash


def hamming_distance(hash1: int, hash2: int) -> int:
    """Menghitung jarak Hamming antara dua perceptual hash 64-bit."""
    xor = (hash1 ^ hash2) & 0xFFFFFFFFFFFFFFFF
    return bin(xor).count("1")


def is_visual_regression(current_hash: int, golden_hash: int, threshold: int = 10) -> bool:
    """Jarak Hamming di atas 10 bit dinyatakan sebagai regresi visual (FR-PR-12)."""
    return hamming_distance(current_hash, golden_hash) > threshold
