"""RUKA VI: Discrete Mathematics — FSM, Invariants, and Digraphs.
Strictly follows RUKA-VI Chapter VII (baris 31-180).
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
import heapq
from typing import Any, Callable, Iterable, Mapping, Sequence


class DAGError(Exception):
    pass


@dataclass(frozen=True)
class Transition:
    source: str
    event: str
    target: str
    guard: str | None = None


class FSM:
    """Finite State Machine formal dengan invarian + analisis statis.
    Invarian dideklarasikan sebagai predikat ber-nama (string) dan diterapkan
    lewat check_invariant() yang mengiterasi SEMUA status terjangkau.
    Legalitas:
    - fire(state, event) mengembalikan status baru ATAU None (ilegal/ditolak)
    - transisi dengan guard gagal = ditolak (bukan senyap dijalankan)
    """

    def __init__(
        self,
        name: str,
        states: Iterable[str],
        transitions: Iterable[Transition],
        initial: str,
        terminal: Iterable[str] = (),
        invariants: Mapping[str, Callable[[str], bool]] | None = None,
    ):
        self.name = name
        self.states: frozenset[str] = frozenset(states)
        self.initial = initial
        self.terminal: frozenset[str] = frozenset(terminal)
        self._delta: dict[tuple[str, str], Transition] = {}
        self.invariants: dict[str, Callable[[str], bool]] = dict(invariants or {})

        for t in transitions:
            if t.source not in self.states or t.target not in self.states:
                raise ValueError(
                    f"transisi {t.source}--{t.event}-->{t.target} menyebut status tak dikenal"
                )
            key = (t.source, t.event)
            if key in self._delta and self._delta[key].target != t.target:
                raise ValueError(f"δ tak deterministik: ({t.source},{t.event}) ganda")
            self._delta[key] = t

        if initial not in self.states:
            raise ValueError(f"initial {initial} bukan anggota S")
        for s in self.terminal:
            if s not in self.states:
                raise ValueError(f"terminal {s} bukan anggota S")

    # ------------------------------------------------------------- operasi
    def fire(self, state: str, event: str) -> str | None:
        """δ(state, event) → status baru, atau None bila ilegal. TANPA efek samping."""
        if state not in self.states:
            raise ValueError(f"status {state} tak dikenal")
        t = self._delta.get((state, event))
        return t.target if t is not None else None

    def fire_checked(self, state: str, event: str) -> str:
        """fire() yang menolak keras bila ilegal — untuk kode produksi."""
        nxt = self.fire(state, event)
        if nxt is None:
            raise ValueError(f"transisi ilegal: ({state}, {event}) pada FSM {self.name}")
        return nxt

    def events_from(self, state: str) -> list[str]:
        if state not in self.states:
            raise ValueError(f"status {state} tak dikenal")
        return sorted({e for (s, e) in self._delta if s == state})

    # ------------------------------------------------------------- analisis
    def reachable_states(self) -> set[str]:
        """BFS dari initial — status yang bisa dicapai. Yang tak terjangkau
        = dead code arsitektural: dideteksi, dilaporkan (analysis.py)."""
        seen = {self.initial}
        q: deque[str] = deque([self.initial])
        while q:
            s = q.popleft()
            for (src, _ev), t in self._delta.items():
                if src == s and t.target not in seen:
                    seen.add(t.target)
                    q.append(t.target)
        return seen

    def dead_states(self) -> set[str]:
        """Status dari mana TIDAK ADA busur keluar (selain terminal sah)."""
        has_out = {src for (src, _e) in self._delta}
        return {s for s in self.states if s not in has_out and s not in self.terminal}

    def unreachable_states(self) -> set[str]:
        return set(self.states) - self.reachable_states()

    def check_invariants(self) -> list[str]:
        """Evaluasi semua invarian atas semua status terjangkau → daftar pelanggaran."""
        violations: list[str] = []
        for s in sorted(self.reachable_states()):
            for inv_name, pred in self.invariants.items():
                if not pred(s):
                    violations.append(f"invarian '{inv_name}' dilanggar di status {s}")
        return violations

    def path_exists(self, src: str, dst: str) -> bool:
        if src not in self.states or dst not in self.states:
            raise ValueError("status tak dikenal")
        seen = {src}
        q: deque[str] = deque([src])
        while q:
            s = q.popleft()
            if s == dst:
                return True
            for (s0, _e), t in self._delta.items():
                if s0 == s and t.target not in seen:
                    seen.add(t.target)
                    q.append(t.target)
        return False

    def as_dict(self) -> dict[str, Any]:
        """Serialisasi (untuk audit/buku): S, E, δ, terminal."""
        return {
            "name": self.name,
            "states": sorted(self.states),
            "initial": self.initial,
            "terminal": sorted(self.terminal),
            "transitions": [
                {
                    "source": t.source,
                    "event": t.event,
                    "target": t.target,
                    "guard": t.guard,
                }
                for t in sorted(
                    self._delta.values(),
                    key=lambda t: (t.source, t.event, t.target),
                )
            ],
        }


# ================================================================== DIGRAF
@dataclass
class Digraph:
    """Digraf berbobot (default bobot 1) — m × m adjacency dict-of-dict."""

    nodes: set[str] = field(default_factory=set)
    _adj: dict[str, dict[str, float]] = field(default_factory=dict)

    def add_node(self, n: str) -> None:
        self.nodes.add(n)
        self._adj.setdefault(n, {})

    def add_edge(self, u: str, v: str, weight: float = 1.0) -> None:
        if weight < 0:
            raise ValueError("bobot tak negatif (Dijkstra)")
        self.add_node(u)
        self.add_node(v)
        self._adj[u][v] = weight

    def successors(self, u: str) -> list[str]:
        return sorted(self._adj.get(u, {}).keys())

    def predecessors(self, v: str) -> list[str]:
        return sorted(u for u in self.nodes if v in self._adj.get(u, {}))

    def edges(self) -> list[tuple[str, str, float]]:
        return [
            (u, v, w)
            for u in sorted(self.nodes)
            for v, w in sorted(self._adj.get(u, {}).items())
        ]

    def edge_weight(self, u: str, v: str) -> float | None:
        return self._adj.get(u, {}).get(v)

    # ------------------------------------------------------------- analisis
    def reachability(self, src: str) -> set[str]:
        if src not in self.nodes:
            raise ValueError(f"node {src} tak dikenal")
        seen = {src}
        q: deque[str] = deque([src])
        while q:
            u = q.popleft()
            for v in self.successors(u):
                if v not in seen:
                    seen.add(v)
                    q.append(v)
        return seen

    def dijkstra(self, src: str, dst: str) -> tuple[float, list[str]]:
        if src not in self.nodes or dst not in self.nodes:
            raise ValueError("node tak dikenal")
        dist = {n: float("inf") for n in self.nodes}
        prev: dict[str, str | None] = {n: None for n in self.nodes}
        dist[src] = 0.0
        pq: list[tuple[float, str]] = [(0.0, src)]

        while pq:
            d, u = heapq.heappop(pq)
            if d > dist[u]:
                continue
            if u == dst:
                break
            for v, w in self._adj.get(u, {}).items():
                if dist[u] + w < dist[v]:
                    dist[v] = dist[u] + w
                    prev[v] = u
                    heapq.heappush(pq, (dist[v], v))

        if dist[dst] == float("inf"):
            return float("inf"), []

        path: list[str] = []
        curr: str | None = dst
        while curr is not None:
            path.append(curr)
            curr = prev[curr]
        path.reverse()
        return dist[dst], path

    def topological_order(self) -> list[str]:
        """Kahn: indegree 0 dulu; SIKLUS → urutan kosong sebagai penanda deterministik."""
        indegree = {n: 0 for n in self.nodes}
        for u in self.nodes:
            for v in self.successors(u):
                indegree[v] += 1
        q: deque[str] = deque(sorted([n for n in self.nodes if indegree[n] == 0]))
        order: list[str] = []
        while q:
            u = q.popleft()
            order.append(u)
            for v in self.successors(u):
                indegree[v] -= 1
                if indegree[v] == 0:
                    q.append(v)
        if len(order) < len(self.nodes):
            return []
        return order

    def transitive_closure(self) -> set[tuple[str, str]]:
        """Warshall O(|V|^3) -> idempotent: (R^+)^+ = R^+."""
        reach: set[tuple[str, str]] = {(u, v) for u, v, _ in self.edges()}
        nodes_list = sorted(self.nodes)
        for k in nodes_list:
            for i in nodes_list:
                for j in nodes_list:
                    if (i, j) in reach or ((i, k) in reach and (k, j) in reach):
                        reach.add((i, j))
        return reach

    def is_partial_order(self) -> bool:
        tc = self.transitive_closure()
        for u, v in tc:
            if u != v and (v, u) in tc:
                return False
        return len(self.topological_order()) == len(self.nodes)


class DAG:
    """Wrapper DAG kompatibel dengan test terdahulu berbasis Digraph."""

    def __init__(self) -> None:
        self.graph = Digraph()

    def add_node(self, node: str) -> None:
        self.graph.add_node(node)

    def add_edge(self, src: str, dst: str) -> None:
        self.graph.add_edge(src, dst)
        if not self.graph.topological_order():
            # Rollback
            del self.graph._adj[src][dst]
            raise DAGError(f"Menambahkan edge {src}->{dst} menciptakan siklus.")

    def topological_sort(self) -> list[str]:
        order = self.graph.topological_order()
        if not order and self.graph.nodes:
            raise DAGError("Graf memuat siklus.")
        return order
