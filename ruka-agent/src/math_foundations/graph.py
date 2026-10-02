# -*- coding: utf-8 -*-
"""Mathematical Foundations — Graph and DAG Utilities.

Menyediakan utilitas analisis graf berarah asiklik (DAG):
deteksi siklus, pengurutan topologis, penentuan level paralel (topological levels),
dan estimasi jalur kritis (critical path).
"""
from __future__ import annotations

from collections import defaultdict, deque
from typing import Mapping, Sequence


def detect_cycles(adjacency: Mapping[str, Sequence[str]]) -> list[list[str]]:
    """Mendeteksi semua siklus pada directed graph menggunakan DFS.

    Returns:
        List berisi urutan siklus (contoh: [['A', 'B', 'C', 'A']]).
    """
    visited: dict[str, int] = {}  # 0=unvisited, 1=visiting, 2=visited
    parent: dict[str, str | None] = {}
    cycles: list[list[str]] = []

    all_nodes = set(adjacency.keys())
    for targets in adjacency.values():
        all_nodes.update(targets)

    for node in all_nodes:
        visited[node] = 0

    def dfs(u: str, path: list[str]) -> None:
        visited[u] = 1
        path.append(u)

        for v in adjacency.get(u, []):
            if visited[v] == 1:
                # Menemukan siklus
                cycle_start_idx = path.index(v)
                cycles.append(path[cycle_start_idx:] + [v])
            elif visited[v] == 0:
                dfs(v, path)

        path.pop()
        visited[u] = 2

    for node in sorted(all_nodes):
        if visited[node] == 0:
            dfs(node, [])

    return cycles


def topological_sort(nodes: Sequence[str], edges: Mapping[str, Sequence[str]]) -> list[str]:
    """Mengurutkan node secara topologis (Kahn's Algorithm).
    Raises ValueError jika graf memiliki siklus.
    """
    in_degree: dict[str, int] = {n: 0 for n in nodes}
    adj: dict[str, list[str]] = defaultdict(list)

    for u, targets in edges.items():
        if u not in in_degree:
            in_degree[u] = 0
        for v in targets:
            adj[u].append(v)
            in_degree[v] = in_degree.get(v, 0) + 1

    queue = deque([n for n, deg in in_degree.items() if deg == 0])
    ordered: list[str] = []

    while queue:
        u = queue.popleft()
        ordered.append(u)
        for v in adj[u]:
            in_degree[v] -= 1
            if in_degree[v] == 0:
                queue.append(v)

    if len(ordered) < len(in_degree):
        raise ValueError("Graf memiliki ketergantungan melingkar (siklus)")

    return ordered


def topological_levels(nodes: Sequence[str], edges: Mapping[str, Sequence[str]]) -> list[list[str]]:
    """Mengelompokkan node menjadi tingkatan (levels) yang dapat dieksekusi secara paralel.
    Level 0 = node tanpa dependensi input.
    """
    in_degree: dict[str, int] = {n: 0 for n in nodes}
    adj: dict[str, list[str]] = defaultdict(list)

    for u, targets in edges.items():
        if u not in in_degree:
            in_degree[u] = 0
        for v in targets:
            adj[u].append(v)
            in_degree[v] = in_degree.get(v, 0) + 1

    current_level = [n for n, deg in in_degree.items() if deg == 0]
    levels: list[list[str]] = []
    processed_count = 0

    while current_level:
        levels.append(sorted(current_level))
        processed_count += len(current_level)
        next_level = []
        for u in current_level:
            for v in adj[u]:
                in_degree[v] -= 1
                if in_degree[v] == 0:
                    next_level.append(v)
        current_level = next_level

    if processed_count < len(in_degree):
        raise ValueError("Graf mengandung siklus; tidak dapat menentukan tingkatan topologis")

    return levels


def critical_path_length(
    nodes: Sequence[str],
    edges: Mapping[str, Sequence[str]],
    durations: Mapping[str, float],
) -> float:
    """Menghitung panjang jalur kritis (critical path) pada DAG berdasarkan durasi tiap node."""
    try:
        topo = topological_sort(nodes, edges)
    except ValueError:
        return 0.0

    earliest_finish: dict[str, float] = {}
    for n in topo:
        cost = float(durations.get(n, 1.0))
        earliest_finish[n] = cost

    for u in topo:
        for v in edges.get(u, []):
            cost_v = float(durations.get(v, 1.0))
            if earliest_finish[u] + cost_v > earliest_finish[v]:
                earliest_finish[v] = earliest_finish[u] + cost_v

    return max(earliest_finish.values()) if earliest_finish else 0.0
