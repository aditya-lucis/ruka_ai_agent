# -*- coding: utf-8 -*-
"""Boss Gate 2 — Shadow Hands Test Suite (FR-HA).

Verifikasi:
- Boss Fight 5:
  - Ruang aksi tertutup lima kata kerja (click, type, scroll, key, wait), aksi asing ditolak keras
  - Trajektori kurva Bezier kuadratik berjitter alami (titik akhir tepat, kelengkungan non-zero)
  - ActionGate fail-closed (kebijakan rusak -> deny, denylist -> deny)
  - Single-writer worker (antrean 64, rate-limit 8 aksi/detik)
  - Gerbang konfirmasi 60s timeout fail-closed
  - Kill Switch tiga pintu (< 200 ms)
  - Audit trail INSERT-only 6-kolom
  - EventBus V3 namespace hands.*
"""
import time
import pytest
from src.gateway.events import EventBus, OrganNamespace
from src.hands import (
    ActionGate,
    AuditTrail,
    ClickAction,
    ConfirmGate,
    HumanMouseTrajectory,
    KeyAction,
    PermissionVerdict,
    RiskLevel,
    SafeInputOS,
    ScrollAction,
    ShadowHands,
    SingleWriterWorker,
    TypeAction,
    WaitAction,
    validate_action,
)


class TestActionSpace:
    def test_five_frozen_actions_only(self):
        # 5 aksi valid
        assert validate_action(ClickAction(100, 200)) is not None
        assert validate_action(TypeAction("halo")) is not None
        assert validate_action(ScrollAction(0, -10)) is not None
        assert validate_action(KeyAction("enter")) is not None
        assert validate_action(WaitAction(100.0)) is not None

        # Aksi asing harus ditolak keras
        class ForeignAction:
            pass

        with pytest.raises(ValueError, match="tidak sah! Ruang aksi Shadow Hands hanya mengizinkan"):
            validate_action(ForeignAction())


class TestHumanMouseBezier:
    def test_bezier_trajectory_curvature_and_accuracy(self):
        mouse = HumanMouseTrajectory(rng_seed=123)
        start = (100, 100)
        target = (500, 400)

        path = mouse.generate_path(start, target, steps=30)
        assert len(path) == 30

        # Titik awal dan akhir tepat
        assert path[0] == start
        assert path[-1] == target

        # Titik lintasan tidak boleh garis lurus kaku (ada deviasi kurva Bezier & jitter)
        # Hitung jarak titik tengah lintasan dari garis lurus start -> target
        mid_pt = path[15]
        # Garis lurus di t=0.5 adalah (300, 250)
        straight_mid = (300, 250)
        dist_from_straight = abs(mid_pt[0] - straight_mid[0]) + abs(mid_pt[1] - straight_mid[1])
        assert dist_from_straight > 5, "Lintasan mouse tidak memiliki kelengkungan kurva alami"


class TestSafeInputOS:
    def test_inverted_modifier_release(self):
        input_os = SafeInputOS(simulate=True)
        # Kombinasi Ctrl+Shift+S
        ok = input_os.press_key_combination("s", modifiers=("ctrl", "shift"))
        assert ok is True

        log = input_os.execution_log
        # Tekan: DOWN:ctrl, DOWN:shift, PRESS:s
        # Lepas TERBALIK: UP:shift, UP:ctrl
        assert log[0] == "DOWN:ctrl"
        assert log[1] == "DOWN:shift"
        assert log[2] == "PRESS:s"
        assert log[3] == "UP:shift"
        assert log[4] == "UP:ctrl"
        assert len(input_os.pressed_modifiers) == 0


class TestActionGateFailClosed:
    def test_fail_closed_and_denylist(self):
        gate = ActionGate(policy_healthy=True)

        # 1. Aksi hijau normal diizinkan
        v1 = gate.evaluate(ClickAction(100, 100))
        assert v1 == PermissionVerdict.ALLOW

        # 2. Konteks denylist (kata sandi/perbankan) langsung DENY
        v2 = gate.evaluate(TypeAction("mypassword123"), target_context="Login form password")
        assert v2 == PermissionVerdict.DENY

        v3 = gate.evaluate(ClickAction(200, 300), target_context="https://klikbca.com/transfer")
        assert v3 == PermissionVerdict.DENY

        # 3. Kebijakan rusak -> Seluruh aksi ditolak (fail-closed mutlak)
        broken_gate = ActionGate(policy_healthy=False)
        v4 = broken_gate.evaluate(ClickAction(10, 10))
        assert v4 == PermissionVerdict.DENY


class TestConfirmGate:
    def test_confirm_timeout_fail_closed(self):
        gate = ConfirmGate(default_timeout_s=0.1)  # 100 ms timeout untuk tes
        action = ClickAction(500, 500)
        ticket = gate.request_confirmation(action, "Format hard drive")

        assert ticket.status == "pending"
        assert gate.is_ticket_valid(ticket.ticket_id) is False

        # Tunggu timeout
        time.sleep(0.15)
        assert ticket.status == "timed_out"
        assert gate.is_ticket_valid(ticket.ticket_id) is False

    def test_confirm_approval_flow(self):
        gate = ConfirmGate(default_timeout_s=10.0)
        action = KeyAction("enter")
        ticket = gate.request_confirmation(action, "Kirim email penting")

        gate.resolve_ticket(ticket.ticket_id, approved=True)
        assert ticket.status == "approved"
        assert gate.is_ticket_valid(ticket.ticket_id) is True


class TestSingleWriterWorkerAndKillSwitch:
    def test_queue_bounding_and_rate_limiting(self):
        worker = SingleWriterWorker(queue_capacity=64, max_rate_per_sec=8.0)
        executed = []

        def dummy_exec(a):
            executed.append(a)
            return True

        # Masukkan 70 aksi (antrean berbatas 64)
        for i in range(70):
            worker.enqueue(ClickAction(i, i), dummy_exec)

        assert worker.queue_size == 64

        # Step 1 berjalan
        res = worker.step(now=1000.0)
        assert res is True
        assert len(executed) == 1

        # Step 2 dipanggil seketika (< 125 ms) -> ditolak pembatas laju
        res2 = worker.step(now=1000.05)
        assert res2 is None
        assert len(executed) == 1

        # Step 2 dipanggil setelah interval 125 ms -> lolos
        res3 = worker.step(now=1000.13)
        assert res3 is True
        assert len(executed) == 2

    def test_kill_switch_under_200ms(self):
        worker = SingleWriterWorker(queue_capacity=64)
        for i in range(50):
            worker.enqueue(ClickAction(i, i), lambda a: None)

        assert worker.queue_size == 50
        latency_ms = worker.trigger_kill_switch()

        assert latency_ms < 200.0
        assert worker.is_killed is True
        assert worker.queue_size == 0


class TestAuditTrail:
    def test_insert_only_audit_log(self):
        audit = AuditTrail(db_path=":memory:")
        row_id = audit.record_action("ClickAction", "(100, 200)", "ALLOW", verified=True)
        assert row_id >= 1

        recent = audit.query_recent(limit=10)
        assert len(recent) == 1
        assert recent[0]["action_type"] == "ClickAction"
        assert recent[0]["verdict"] == "ALLOW"
        assert recent[0]["verified"] is True
        audit.close()


class TestShadowHandsPipeline:
    def test_full_pipeline_execution(self):
        bus = EventBus()
        hands = ShadowHands(event_bus=bus, simulate_input=True)

        events = []
        bus.subscribe("hands.*", lambda e: events.append(e))

        # 1. Aksi Green lolos
        res = hands.execute_action(ClickAction(250, 300), target_context="Text Editor")
        assert res["status"] == "success"

        # 2. Aksi Red butuh konfirmasi
        red_res = hands.execute_action(KeyAction("delete"), risk_level=RiskLevel.RED)
        assert red_res["status"] == "awaiting_or_invalid_confirmation"

        # Minta tiket konfirmasi
        ticket = hands.request_confirmation(KeyAction("delete"), "Hapus berkas konfigurasi")
        hands.resolve_confirmation(ticket.ticket_id, approved=True)

        # Eksekusi dengan tiket yang sah
        red_ok = hands.execute_action(KeyAction("delete"), risk_level=RiskLevel.RED, ticket_id=ticket.ticket_id)
        assert red_ok["status"] == "success"

        # 3. Kill switch darurat
        kill_lat = hands.kill_all()
        assert kill_lat < 200.0

        bus.drain()
        topics = [e.event_type for e in events]
        assert "hands.action" in topics
        assert "hands.confirm_request" in topics
        assert "hands.confirm_result" in topics
        assert "hands.kill" in topics
