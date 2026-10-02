# -*- coding: utf-8 -*-
"""RUKA Mathematical Foundations.

Lapisan fondasi matematika murni untuk Marquis of Trendamis:
- Linear algebra (l2_normalize, cosine_similarity, batch_cosine)
- Probability & Bayesian reasoning (bayesian_update, shannon_entropy, calibration)
- Optimization (utility_score, softmax_select, pareto_frontier_indices)
- Information Theory (kl_divergence, memory_surprise, importance_score)
- Graph & DAGs (detect_cycles, topological_sort, topological_levels, critical_path_length)
- Control Theory (loop_health, BudgetController)
- Statistical Learning (RunningStats, exponential_moving_average, wasserstein_distance_1d)
- Formal Types (Score, Belief, BeliefState)
"""
from __future__ import annotations

from src.math_foundations.types import Score, Belief, BeliefState
from src.math_foundations.linear import (
    l2_normalize,
    cosine_similarity,
    batch_cosine,
    euclidean_distance,
    batch_euclidean,
    vector_projection,
    orthonormalize,
)
from src.math_foundations.probability import (
    shannon_entropy,
    bayesian_update,
    brier_score,
    expected_calibration_error,
    softmax,
    temperature_scale,
)
from src.math_foundations.optimization import (
    utility_score,
    softmax_select,
    pareto_frontier_indices,
)
from src.math_foundations.information import (
    kl_divergence,
    memory_surprise,
    importance_score,
    mutual_information_discrete,
)
from src.math_foundations.graph import (
    detect_cycles,
    topological_sort,
    topological_levels,
    critical_path_length,
)
from src.math_foundations.control import (
    loop_health,
    BudgetController,
)
from src.math_foundations.statistical import (
    RunningStats,
    exponential_moving_average,
    wasserstein_distance_1d,
    classification_metrics,
)

__all__ = [
    # Types
    "Score",
    "Belief",
    "BeliefState",
    # Linear
    "l2_normalize",
    "cosine_similarity",
    "batch_cosine",
    "euclidean_distance",
    "batch_euclidean",
    "vector_projection",
    "orthonormalize",
    # Probability
    "shannon_entropy",
    "bayesian_update",
    "brier_score",
    "expected_calibration_error",
    "softmax",
    "temperature_scale",
    # Optimization
    "utility_score",
    "softmax_select",
    "pareto_frontier_indices",
    # Information
    "kl_divergence",
    "memory_surprise",
    "importance_score",
    "mutual_information_discrete",
    # Graph
    "detect_cycles",
    "topological_sort",
    "topological_levels",
    "critical_path_length",
    # Control
    "loop_health",
    "BudgetController",
    # Statistical
    "RunningStats",
    "exponential_moving_average",
    "wasserstein_distance_1d",
    "classification_metrics",
]
