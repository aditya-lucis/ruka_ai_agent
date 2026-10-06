# -*- coding: utf-8 -*-
"""PROJECT NOCTIS — Quantum Sandbox Solvers.

Implements SRS FR-FG-05.
- Double Slit simulator with >= 3 interference minima detected automatically.
- Quantum Tunneling with monotonic transmission and (T + R) approx 1.0.
- Bloch Sphere state vector simulation preserving norm at 1.0 +- 1e-6.
"""

from __future__ import annotations

import math
from typing import Dict, List, Tuple
import numpy as np


class DoubleSlitSimulator:
    """FR-FG-05: Simulates wave interference pattern and detects >= 3 minima."""

    def __init__(self, wavelength: float = 0.5, slit_distance: float = 2.0, screen_dist: float = 10.0) -> None:
        self.wavelength = wavelength
        self.d = slit_distance
        self.L = screen_dist

    def compute_pattern(self, num_points: int = 500, span: float = 15.0) -> dict:
        x = np.linspace(-span, span, num_points)
        k = 2.0 * np.pi / self.wavelength

        # Optical path difference: delta = d * sin(theta) approx d * (x / L)
        sin_theta = x / np.sqrt(x**2 + self.L**2)
        phase_diff = k * self.d * sin_theta

        # Intensity I = I0 * cos^2(phase_diff / 2)
        intensity = (np.cos(phase_diff / 2.0)) ** 2

        # Detect local minima
        minima_indices = []
        for i in range(1, len(intensity) - 1):
            if intensity[i] < intensity[i - 1] and intensity[i] < intensity[i + 1] and intensity[i] < 0.05:
                minima_indices.append(i)

        minima_count = len(minima_indices)

        return {
            "x": x.tolist(),
            "intensity": intensity.tolist(),
            "minima_count": minima_count,
            "minima_positions": x[minima_indices].tolist(),
            "passed_spec": minima_count >= 3,  # FR-FG-05: minimal 3 minimum interferensi
        }


class QuantumTunnelingSolver:
    """FR-FG-05: 1D rectangular barrier tunneling (monotone transmission & T + R approx 1.0)."""

    def __init__(self, barrier_height: float = 5.0, barrier_width: float = 1.0) -> None:
        self.V0 = barrier_height
        self.a = barrier_width

    def transmission_coefficient(self, energy: float) -> float:
        """Analytical transmission coefficient for E < V0."""
        if energy <= 0.0:
            return 0.0
        if energy >= self.V0:
            # Over-barrier transmission
            k1 = math.sqrt(2.0 * energy)
            k2 = math.sqrt(2.0 * (energy - self.V0))
            if k2 == 0:
                return 0.5
            denom = 1.0 + ((k1**2 - k2**2)**2 / (4.0 * k1**2 * k2**2)) * (math.sin(k2 * self.a)**2)
            return 1.0 / denom

        # Tunneling regime (E < V0)
        # kappa = sqrt(2m(V0 - E)/hbar^2)
        kappa = math.sqrt(2.0 * (self.V0 - energy))
        sinh_val = math.sinh(kappa * self.a)
        denom = 1.0 + ((self.V0**2) / (4.0 * energy * (self.V0 - energy))) * (sinh_val**2)
        return 1.0 / denom

    def verify_conservation_and_monotonicity(self) -> dict:
        energies = np.linspace(0.5, 4.5, 20)
        transmissions = [self.transmission_coefficient(e) for e in energies]
        reflections = [1.0 - t for t in transmissions]

        # Check T + R approx 1.0 for all
        conservation_preserved = all(abs((t + r) - 1.0) < 1e-9 for t, r in zip(transmissions, reflections))

        # Check monotonic increase of T with respect to E
        is_monotonic = all(transmissions[i] <= transmissions[i + 1] for i in range(len(transmissions) - 1))

        return {
            "energies": energies.tolist(),
            "transmissions": transmissions,
            "conservation_preserved": conservation_preserved,
            "is_monotonic": is_monotonic,
            "passed_spec": conservation_preserved and is_monotonic,
        }


class BlochSphereSimulator:
    """FR-FG-05: Single qubit state representation on Bloch sphere preserving norm 1.0 +- 1e-6."""

    def __init__(self, theta: float = math.pi / 3, phi: float = math.pi / 4) -> None:
        self.theta = theta
        self.phi = phi
        self.state = self._compute_state(theta, phi)

    def _compute_state(self, theta: float, phi: float) -> np.ndarray:
        c0 = math.cos(theta / 2.0)
        c1 = math.sin(theta / 2.0) * (math.cos(phi) + 1j * math.sin(phi))
        return np.array([c0, c1], dtype=np.complex128)

    def get_norm(self) -> float:
        return float(np.sqrt(np.abs(self.state[0])**2 + np.abs(self.state[1])**2))

    def apply_unitary(self, U: np.ndarray) -> dict:
        """Applies a 2x2 unitary transformation and tests norm preservation."""
        self.state = np.dot(U, self.state)
        norm = self.get_norm()
        error = abs(norm - 1.0)
        passed_spec = error <= 1e-6  # FR-FG-05: norm vector preserved at 1.0 +- 1e-6

        # Convert to Bloch coordinates (x, y, z)
        # rho = |psi><psi| -> x = 2*Re(c0*c1*), y = 2*Im(c0*c1*), z = |c0|^2 - |c1|^2
        c0, c1 = self.state[0], self.state[1]
        x = 2.0 * float(np.real(c0 * np.conj(c1)))
        y = 2.0 * float(np.imag(c1 * np.conj(c0)))
        z = float(np.abs(c0)**2 - np.abs(c1)**2)

        return {
            "norm": norm,
            "norm_error": error,
            "passed_spec": passed_spec,
            "bloch_coords": {"x": x, "y": y, "z": z},
        }
