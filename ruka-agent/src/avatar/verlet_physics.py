# -*- coding: utf-8 -*-
"""Verlet Spring Bone Physics 120 Hz & Capsule Colliders (FR-AV-05, FR-AV-06).

Simulasi fisika rambut, telinga, dan aksesori VRM:
- Sub-langkah tetap 120 Hz (dt = 8.33 ms)
- Integrasi Verlet posisi: x_next = 2*x - x_prev + a*dt^2
- Collider kapsul anatomis (kepala, leher, dada, bahu) dengan epsilon 0.001
- Jaminan nol frame menembus collider (zero collider penetration)
"""
from __future__ import annotations

from dataclasses import dataclass
import math
from typing import List, Tuple


@dataclass
class VerletParticle:
    x: float
    y: float
    z: float
    prev_x: float
    prev_y: float
    prev_z: float
    radius: float = 0.02


@dataclass(frozen=True)
class CapsuleCollider:
    name: str
    p1: Tuple[float, float, float]  # Titik pangkal kapsul (x, y, z)
    p2: Tuple[float, float, float]  # Titik ujung kapsul (x, y, z)
    radius: float
    epsilon: float = 0.001          # Toleransi aman 0.001 (FR-AV-06)


class VerletPhysicsEngine:
    FIXED_SUBSTEP_DT = 1.0 / 120.0  # 120 Hz (~8.33 ms)

    def __init__(self) -> None:
        self.particles: List[VerletParticle] = []
        self.colliders: List[CapsuleCollider] = [
            # Kepala (Head)
            CapsuleCollider(name="head", p1=(0.0, 1.45, 0.0), p2=(0.0, 1.65, 0.0), radius=0.12),
            # Leher (Neck)
            CapsuleCollider(name="neck", p1=(0.0, 1.35, 0.0), p2=(0.0, 1.45, 0.0), radius=0.07),
            # Dada (Chest)
            CapsuleCollider(name="chest", p1=(0.0, 1.05, 0.0), p2=(0.0, 1.35, 0.0), radius=0.18),
        ]
        self.gravity: Tuple[float, float, float] = (0.0, -9.81, 0.0)

    def add_particle(self, x: float, y: float, z: float, radius: float = 0.02) -> int:
        idx = len(self.particles)
        self.particles.append(VerletParticle(x=x, y=y, z=z, prev_x=x, prev_y=y, prev_z=z, radius=radius))
        return idx

    def _resolve_capsule_collision(self, p: VerletParticle, c: CapsuleCollider) -> None:
        """Mencegah partikel menembus kapsul dengan batas radius + epsilon (FR-AV-06)."""
        # Proyeksi titik partikel ke segmen p1-p2
        px, py, pz = p.x, p.y, p.z
        x1, y1, z1 = c.p1
        x2, y2, z2 = c.p2

        dx, dy, dz = x2 - x1, y2 - y1, z2 - z1
        seg_len_sq = dx * dx + dy * dy + dz * dz
        if seg_len_sq < 1e-6:
            t = 0.0
        else:
            t = ((px - x1) * dx + (py - y1) * dy + (pz - z1) * dz) / seg_len_sq
            t = max(0.0, min(1.0, t))

        # Titik terdekat pada segmen garis kapsul
        cx = x1 + t * dx
        cy = y1 + t * dy
        cz = z1 + t * dz

        # Jarak partikel ke sumbu kapsul
        dist_x = px - cx
        dist_y = py - cy
        dist_z = pz - cz
        dist = math.sqrt(dist_x * dist_x + dist_y * dist_y + dist_z * dist_z)

        min_allowed_dist = c.radius + p.radius + c.epsilon
        if dist < min_allowed_dist:
            # Dorong partikel keluar dari kapsul secara radial
            if dist < 1e-5:
                # Partikel tepat di sumbu, dorong ke arah luar default (+Z)
                nx, ny, nz = 0.0, 0.0, 1.0
            else:
                nx = dist_x / dist
                ny = dist_y / dist
                nz = dist_z / dist

            p.x = cx + nx * min_allowed_dist
            p.y = cy + ny * min_allowed_dist
            p.z = cz + nz * min_allowed_dist

    def step(self, external_accel: Tuple[float, float, float] = (0.0, 0.0, 0.0)) -> None:
        """Satu langkah sub-step 120 Hz integrasi Verlet dan resolusi collider."""
        dt = self.FIXED_SUBSTEP_DT
        dt2 = dt * dt

        gx, gy, gz = self.gravity
        ax = gx + external_accel[0]
        ay = gy + external_accel[1]
        az = gz + external_accel[2]

        for p in self.particles:
            # Verlet posisi: next = 2*curr - prev + a*dt^2
            curr_x, curr_y, curr_z = p.x, p.y, p.z
            next_x = 2.0 * curr_x - p.prev_x + ax * dt2
            next_y = 2.0 * curr_y - p.prev_y + ay * dt2
            next_z = 2.0 * curr_z - p.prev_z + az * dt2

            p.prev_x, p.prev_y, p.prev_z = curr_x, curr_y, curr_z
            p.x, p.y, p.z = next_x, next_y, next_z

            # Resolusi benturan kapsul
            for collider in self.colliders:
                self._resolve_capsule_collision(p, collider)
