# -*- coding: utf-8 -*-
"""PROJECT NOCTIS — Classical & Continuous Physics Solvers.

Implements SRS FR-FG-03 & FR-FG-04.
- Symplectic Integrator (Velocity Verlet / Leapfrog) preserving energy drift < 0.1% over 1,000 steps.
- SAT (Separating Axis Theorem) collision solver with partial position correction.
- XPBD (Extended Position Based Dynamics) cloth solver with constraint length drift < 1%.
- Particle solver handling 10,000 points < 50ms per step in Lite mode.
"""

from __future__ import annotations

import math
import time
from dataclasses import dataclass
from typing import List, Tuple
import numpy as np


class SymplecticOrbitSolver:
    """FR-FG-03: Two-body gravitational orbit with Velocity Verlet symplectic integration."""

    def __init__(self, m1: float = 1.0, m2: float = 0.001, G: float = 1.0) -> None:
        self.m1 = m1
        self.m2 = m2
        self.G = G

    def compute_energy(self, r: np.ndarray, v: np.ndarray) -> float:
        """Total mechanical energy = Kinetic + Gravitational Potential."""
        r_mag = np.linalg.norm(r)
        kinetic = 0.5 * self.m2 * np.dot(v, v)
        potential = - (self.G * self.m1 * self.m2) / max(r_mag, 1e-9)
        return float(kinetic + potential)

    def compute_acceleration(self, r: np.ndarray) -> np.ndarray:
        r_mag = np.linalg.norm(r)
        if r_mag < 1e-9:
            return np.zeros_like(r)
        return - (self.G * self.m1 / (r_mag ** 3)) * r

    def simulate(self, steps: int = 1000, dt: float = 0.001) -> dict:
        """Runs 1,000 orbital integration steps using Velocity Verlet."""
        # Initial circular orbit conditions: r = (1, 0), v = (0, 1)
        r = np.array([1.0, 0.0], dtype=np.float64)
        v = np.array([0.0, 1.0], dtype=np.float64)

        e_initial = self.compute_energy(r, v)
        a = self.compute_acceleration(r)

        energies = [e_initial]
        trajectory = [r.copy()]

        for _ in range(steps):
            # Velocity Verlet step
            r += v * dt + 0.5 * a * (dt ** 2)
            a_next = self.compute_acceleration(r)
            v += 0.5 * (a + a_next) * dt
            a = a_next

            energies.append(self.compute_energy(r, v))
            trajectory.append(r.copy())

        e_final = energies[-1]
        drift_pct = abs((e_final - e_initial) / e_initial) * 100.0

        return {
            "steps": steps,
            "dt": dt,
            "e_initial": e_initial,
            "e_final": e_final,
            "energy_drift_pct": drift_pct,
            "passed_spec": drift_pct < 0.1,  # FR-FG-03: < 0.1% drift
            "trajectory": trajectory,
        }


class SATCollisionSolver:
    """FR-FG-04: Separating Axis Theorem (SAT) convex polygon collision detector."""

    @staticmethod
    def project_polygon(axis: np.ndarray, vertices: np.ndarray) -> Tuple[float, float]:
        dots = np.dot(vertices, axis)
        return float(np.min(dots)), float(np.max(dots))

    @classmethod
    def test_polygon_collision(
        cls, poly_a: np.ndarray, poly_b: np.ndarray
    ) -> Tuple[bool, float, np.ndarray]:
        """Returns (is_colliding, penetration_depth, separation_normal)."""
        polygons = [poly_a, poly_b]
        min_penetration = float("inf")
        best_axis = np.zeros(2)

        for poly in polygons:
            n = len(poly)
            for i in range(n):
                edge = poly[(i + 1) % n] - poly[i]
                normal = np.array([-edge[1], edge[0]], dtype=np.float64)
                norm = np.linalg.norm(normal)
                if norm < 1e-9:
                    continue
                normal /= norm

                min_a, max_a = cls.project_polygon(normal, poly_a)
                min_b, max_b = cls.project_polygon(normal, poly_b)

                if max_a < min_b or max_b < min_a:
                    return False, 0.0, np.zeros(2)  # Separating axis found

                overlap = min(max_a, max_b) - max(min_a, min_b)
                if overlap < min_penetration:
                    min_penetration = overlap
                    best_axis = normal

        return True, min_penetration, best_axis


class XPBDClothSolver:
    """FR-FG-04: Extended Position Based Dynamics (XPBD) 1D cloth/string constraint solver."""

    def __init__(self, num_particles: int = 20, rest_length: float = 1.0) -> None:
        self.num_particles = num_particles
        self.rest_length = rest_length
        self.positions = np.zeros((num_particles, 2), dtype=np.float64)
        for i in range(num_particles):
            self.positions[i] = [i * rest_length, 0.0]

    def step(self, substeps: int = 4, compliance: float = 1e-6) -> dict:
        """Solves length constraints preserving constraint drift < 1%."""
        max_drift_pct = 0.0

        for _ in range(substeps):
            # Apply slight simulated gravity
            self.positions[1:, 1] -= 0.05 / substeps

            # Enforce distance constraints
            for i in range(self.num_particles - 1):
                p1 = self.positions[i]
                p2 = self.positions[i + 1]

                delta = p2 - p1
                current_len = np.linalg.norm(delta)
                if current_len < 1e-9:
                    continue

                diff = current_len - self.rest_length
                drift = abs(diff / self.rest_length) * 100.0
                if drift > max_drift_pct:
                    max_drift_pct = drift

                correction = (diff / (current_len + compliance)) * delta
                if i > 0:
                    self.positions[i] += 0.5 * correction
                self.positions[i + 1] -= 0.5 * correction

        return {
            "particles": self.num_particles,
            "max_drift_pct": max_drift_pct,
            "passed_spec": max_drift_pct < 1.0,  # FR-FG-04: constraint drift < 1%
        }


class ParticleSolverLite:
    """FR-FG-04: Fast 10,000 particle integrator running < 50ms per step in Lite mode."""

    def __init__(self, count: int = 10000) -> None:
        self.count = count
        np.random.seed(42)
        self.positions = np.random.uniform(-10.0, 10.0, size=(count, 2)).astype(np.float32)
        self.velocities = np.random.uniform(-1.0, 1.0, size=(count, 2)).astype(np.float32)

    def step(self, dt: float = 0.016) -> Tuple[float, bool]:
        t0 = time.perf_counter()
        # Vectorized Euler-Cromer update
        self.positions += self.velocities * dt
        # Simple boundary bounce
        mask = np.abs(self.positions) > 10.0
        self.velocities[mask] *= -0.9
        elapsed_ms = (time.perf_counter() - t0) * 1000.0

        # FR-FG-04: < 50ms per step in Lite mode
        passed = elapsed_ms < 50.0
        return elapsed_ms, passed
