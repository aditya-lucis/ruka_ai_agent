"""Tests for RUKA VI Discrete Mathematics (Part VII & XXV).
Strictly verifies:
- Finite State Machine: reachability BFS, dead state detection, invariant checking, guard enforcement
- Digraph: weighted edges, Dijkstra shortest path, Kahn topological sort (deterministic empty list on cycle)
- Transitive closure: Warshall O(|V|^3) idempotence (R^+)^+ = R^+
- Poset (Partial Order) properties: irreflexivity / acyclicity
- DAG wrapper: cycle rejection on edge addition with automatic rollback
"""

import pytest

from ruka_companion.math.discrete import (
    Transition,
    FSM,
    Digraph,
    DAG,
    DAGError,
    topological_order,
)


class TestFSMInvariants:
    def test_basic_transitions_and_fire(self):
        fsm = FSM(
            name="test_fsm",
            states=["A", "B", "C"],
            transitions=[
                Transition("A", "go_b", "B"),
                Transition("B", "go_c", "C"),
            ],
            initial="A",
            terminal=["C"],
        )
        assert fsm.fire("A", "go_b") == "B"
        assert fsm.fire("B", "go_c") == "C"
        # Illegal transition
        assert fsm.fire("A", "go_c") is None

    def test_guard_enforcement(self):
        fsm = FSM(
            name="guarded_fsm",
            states=["READY", "ACTION"],
            transitions=[
                Transition("READY", "do_action", "ACTION", guard="has_permission"),
            ],
            initial="READY",
            guards={"has_permission": lambda ctx: bool(ctx.get("allowed", False))},
        )
        # Guard fails -> returns None
        assert fsm.fire("READY", "do_action", ctx={"allowed": False}) is None
        # Guard passes -> returns target
        assert fsm.fire("READY", "do_action", ctx={"allowed": True}) == "ACTION"

    def test_reachability_and_unreachable_states(self):
        fsm = FSM(
            name="reach_fsm",
            states=["S0", "S1", "S2", "ORPHAN"],
            transitions=[
                Transition("S0", "e1", "S1"),
                Transition("S1", "e2", "S2"),
            ],
            initial="S0",
            terminal=["S2"],
        )
        assert fsm.reachable_states() == {"S0", "S1", "S2"}
        assert fsm.unreachable_states() == {"ORPHAN"}

    def test_dead_state_detection(self):
        # A state with no outgoing transitions that is NOT terminal is a dead state
        fsm = FSM(
            name="dead_fsm",
            states=["A", "DEAD", "DONE"],
            transitions=[
                Transition("A", "to_dead", "DEAD"),
                Transition("A", "to_done", "DONE"),
            ],
            initial="A",
            terminal=["DONE"],
        )
        assert "DEAD" in fsm.dead_states()
        assert "DONE" not in fsm.dead_states()

    def test_check_invariants(self):
        fsm = FSM(
            name="inv_fsm",
            states=["SAFE_1", "SAFE_2", "UNSAFE"],
            transitions=[
                Transition("SAFE_1", "step", "SAFE_2"),
                Transition("SAFE_2", "bad_step", "UNSAFE"),
            ],
            initial="SAFE_1",
            invariants={"no_unsafe": lambda s: s != "UNSAFE"},
        )
        violations = fsm.check_invariants()
        assert len(violations) == 1
        assert "UNSAFE" in violations[0]


class TestDigraphAndShortestPath:
    def test_dijkstra_shortest_path(self):
        g = Digraph()
        # A --(1)--> B --(2)--> D
        # A --(4)--> C --(1)--> D
        g.add_edge("A", "B", 1.0)
        g.add_edge("B", "D", 2.0)
        g.add_edge("A", "C", 4.0)
        g.add_edge("C", "D", 1.0)

        dist, path = g.dijkstra("A", "D")
        assert dist == pytest.approx(3.0)
        assert path == ["A", "B", "D"]

    def test_dijkstra_unreachable(self):
        g = Digraph()
        g.add_node("A")
        g.add_node("B")
        dist, path = g.dijkstra("A", "B")
        assert dist == float("inf")
        assert path == []

    def test_negative_weight_rejected(self):
        g = Digraph()
        with pytest.raises(ValueError):
            g.add_edge("A", "B", -1.0)

    def test_reachability(self):
        g = Digraph()
        g.add_edge("A", "B")
        g.add_edge("B", "C")
        g.add_node("ISOLATED")

        reach = g.reachability("A")
        assert reach == {"A", "B", "C"}
        assert "ISOLATED" not in reach


class TestTopologicalSortAndWarshall:
    def test_topological_sort_linear(self):
        g = Digraph()
        g.add_edge("1", "2")
        g.add_edge("2", "3")
        g.add_edge("3", "4")
        order = g.topological_order()
        assert order == ["1", "2", "3", "4"]

    def test_topological_sort_branching(self):
        g = Digraph()
        g.add_edge("init", "db")
        g.add_edge("init", "cache")
        g.add_edge("db", "api")
        g.add_edge("cache", "api")
        order = g.topological_order()
        assert order.index("init") < order.index("db")
        assert order.index("init") < order.index("cache")
        assert order.index("db") < order.index("api")
        assert order.index("cache") < order.index("api")

    def test_cycle_returns_empty_order_deterministically(self):
        g = Digraph()
        g.add_edge("A", "B")
        g.add_edge("B", "C")
        g.add_edge("C", "A")
        assert g.topological_order() == []
        assert topological_order(g) == []

    def test_transitive_closure_idempotence(self):
        g = Digraph()
        g.add_edge("A", "B")
        g.add_edge("B", "C")
        g.add_edge("C", "D")

        tc = g.transitive_closure()
        assert ("A", "D") in tc
        assert ("A", "C") in tc
        assert ("B", "D") in tc

        # Idempotence: build a new digraph with edges from tc, closure must equal tc
        g_tc = Digraph()
        for u, v in tc:
            g_tc.add_edge(u, v)
        assert g_tc.transitive_closure() == tc

    def test_is_partial_order(self):
        # A DAG is a strict partial order
        g_dag = Digraph()
        g_dag.add_edge("A", "B")
        g_dag.add_edge("B", "C")
        assert g_dag.is_partial_order() is True

        # Graph with cycle is not a partial order
        g_cycle = Digraph()
        g_cycle.add_edge("A", "B")
        g_cycle.add_edge("B", "A")
        assert g_cycle.is_partial_order() is False


class TestDAGWrapper:
    def test_dag_cycle_prevention_and_rollback(self):
        dag = DAG()
        dag.add_edge("A", "B")
        dag.add_edge("B", "C")

        # Adding C -> A would form a cycle
        with pytest.raises(DAGError):
            dag.add_edge("C", "A")

        # Verify rollback: graph remains valid and sortable
        assert dag.topological_sort() == ["A", "B", "C"]


# ============================================================ Extended Tests
class TestFSMExtended:
    def _make_fsm(self):
        return FSM(
            name="ext_fsm",
            states=["A", "B", "C", "D"],
            transitions=[
                Transition("A", "go_b", "B"),
                Transition("B", "go_c", "C"),
                Transition("C", "go_d", "D"),
                Transition("A", "go_d", "D"),
            ],
            initial="A",
            terminal=["D"],
        )

    def test_fire_checked_raises_on_illegal(self):
        fsm = self._make_fsm()
        with pytest.raises(ValueError):
            fsm.fire_checked("A", "go_c")

    def test_fire_checked_succeeds_legal(self):
        fsm = self._make_fsm()
        assert fsm.fire_checked("A", "go_b") == "B"

    def test_events_from(self):
        fsm = self._make_fsm()
        events = fsm.events_from("A")
        assert "go_b" in events
        assert "go_d" in events

    def test_path_exists(self):
        fsm = self._make_fsm()
        assert fsm.path_exists("A", "D") is True
        assert fsm.path_exists("D", "A") is False

    def test_as_dict_serialization(self):
        fsm = self._make_fsm()
        d = fsm.as_dict()
        assert d["name"] == "ext_fsm"
        assert "A" in d["states"]
        assert d["initial"] == "A"
        assert len(d["transitions"]) == 4

    def test_unknown_state_fire_raises(self):
        fsm = self._make_fsm()
        with pytest.raises(ValueError):
            fsm.fire("UNKNOWN", "go_b")

    def test_nondeterministic_transition_rejected(self):
        with pytest.raises(ValueError):
            FSM(
                name="nondet",
                states=["A", "B", "C"],
                transitions=[
                    Transition("A", "go", "B"),
                    Transition("A", "go", "C"),
                ],
                initial="A",
            )

    def test_no_dead_states_when_all_terminal(self):
        fsm = FSM(
            name="all_terminal",
            states=["START", "END"],
            transitions=[Transition("START", "done", "END")],
            initial="START",
            terminal=["END"],
        )
        assert fsm.dead_states() == set()


class TestDigraphExtended:
    def test_predecessors(self):
        g = Digraph()
        g.add_edge("A", "B")
        g.add_edge("C", "B")
        preds = g.predecessors("B")
        assert "A" in preds
        assert "C" in preds

    def test_successors(self):
        g = Digraph()
        g.add_edge("A", "B")
        g.add_edge("A", "C")
        succs = g.successors("A")
        assert succs == ["B", "C"]

    def test_edge_weight(self):
        g = Digraph()
        g.add_edge("X", "Y", 3.5)
        assert g.edge_weight("X", "Y") == 3.5
        assert g.edge_weight("Y", "X") is None

    def test_edges_listing(self):
        g = Digraph()
        g.add_edge("A", "B", 1.0)
        g.add_edge("B", "C", 2.0)
        edges = g.edges()
        assert len(edges) == 2
        assert ("A", "B", 1.0) in edges

    def test_single_node_reachability(self):
        g = Digraph()
        g.add_node("SOLO")
        assert g.reachability("SOLO") == {"SOLO"}


class TestDAGExtended:
    def test_dag_add_node_only(self):
        dag = DAG()
        dag.add_node("X")
        dag.add_node("Y")
        order = dag.topological_sort()
        assert "X" in order
        assert "Y" in order

    def test_dag_diamond_dependency(self):
        dag = DAG()
        dag.add_edge("A", "B")
        dag.add_edge("A", "C")
        dag.add_edge("B", "D")
        dag.add_edge("C", "D")
        order = dag.topological_sort()
        assert order.index("A") < order.index("B")
        assert order.index("A") < order.index("C")
        assert order.index("B") < order.index("D")
        assert order.index("C") < order.index("D")

