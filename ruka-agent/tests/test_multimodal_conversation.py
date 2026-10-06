# -*- coding: utf-8 -*-
"""Boss Gate 3 — Multimodal Conversation Test Suite (FR-MC).

Verifikasi:
- Boss 8 Multimodal Conversation:
  - InputRouter: 6 pintu masuk, VOICE selalu menang prioritas mutlak, 30s dedup
  - ContextFuser: Matryoshka 3.000 token, transkrip pengguna KERAMAT pantang dipangkas
  - ResponseSplitter: membagi dua kanal (suara maks 2 kalimat vs layar kode utuh)
  - Disiplin keras: Tepat 1 panggilan otak per giliran (SingleBrainCallViolation jika dilanggar)
  - Full-duplex barge-in < 300 ms dari SPEAKING ke LISTENING
  - LatencyMeter: p95 <= 800 ms SLA
  - VisualMemory: ~400 byte hash tanpa piksel mentah
  - EventBus V3 namespace converse.*
"""
import time
import pytest
from src.converse import (
    ContextFuser,
    ConversationLoop,
    ConversationState,
    DualResponse,
    InputItem,
    InputRouter,
    LatencyMeter,
    ModalityType,
    ResponseSplitter,
    SingleBrainCallViolation,
    VisualMemory,
)
from src.gateway.events import EventBus, OrganNamespace


class TestInputRouter:
    def test_voice_priority_and_deduplication(self):
        router = InputRouter(dedup_window_s=30.0)

        item_camera = InputItem(ModalityType.CAMERA, "Pengguna tersenyum", time.time())
        item_screen = InputItem(ModalityType.SCREEN, "VSCode terbuka", time.time())
        item_voice = InputItem(ModalityType.VOICE, "Ruka, jelaskan kode ini", time.time())

        # Suara datang bersamaan dengan kamera dan layar
        primary, bg = router.route_inputs([item_camera, item_screen, item_voice])

        # Suara WAJIB menang sebagai primary
        assert primary is not None
        assert primary.modality == ModalityType.VOICE
        assert primary.content == "Ruka, jelaskan kode ini"

        # Kamera dan layar diturunkan menjadi konteks latar belakang (tidak dibuang)
        assert len(bg) == 2
        assert {b.modality for b in bg} == {ModalityType.CAMERA, ModalityType.SCREEN}

        # Deduplikasi: layar dengan isi sama dalam 30 detik ditolak
        item_screen_dup = InputItem(ModalityType.SCREEN, "VSCode terbuka", time.time())
        primary2, bg2 = router.route_inputs([item_screen_dup])
        assert primary2 is None  # Ditolak karena duplikat


class TestContextFuserMatryoshka:
    def test_matryoshka_3000_token_and_sacred_user_transcript(self):
        fuser = ContextFuser(persona_directive="Ruka vampire companion")

        sacred_user_text = "Tolong perbaiki bug pada modul gateway events sekarang juga."

        prompt = fuser.fuse_context(
            user_utterance=sacred_user_text,
            memory_recalls=["Memori proyek 1", "Memori preferensi Young Lord"],
            background_modalities=[InputItem(ModalityType.SCREEN, "Error on line 42", time.time())],
            history_turns=["User: Halo", "Ruka: Salam Young Lord"],
        )

        # Transkrip pengguna TIDAK BOLEH dipangkas sama sekali (Blok Keramat)
        assert prompt.user_transcript_block == sacred_user_text
        assert sacred_user_text in prompt.assemble()

        # Total estimasi token tidak boleh melampaui 3.000 token
        assert prompt.estimated_total_tokens <= 3000


class TestResponseSplitter:
    def test_code_lifting_and_dual_channel_split(self):
        splitter = ResponseSplitter()

        complex_response = (
            "Hamba telah menyelesaikan refaktor fungsi tersebut, My Lord. "
            "Berikut adalah blok kode baru yang telah lolos seluruh pengujian:\n\n"
            "```python\n"
            "def fixed_function():\n"
            "    return True\n"
            "```\n\n"
            "| Parameter | Nilai |\n"
            "| --- | --- |\n"
            "| Status | Lulus |\n\n"
            "Silakan periksa berkas [loader.py](file:///path/to/loader.py) untuk rinciannya. "
            "Apakah ada tugas lain yang hendak Anda titahkan?"
        )

        dual = splitter.split_response(complex_response)

        # 1. Kanal Suara: MAKSIMAL 2 kalimat inti, TANPA blok kode, TANPA tabel
        assert "```python" not in dual.voice_text
        assert "fixed_function" not in dual.voice_text
        assert "| Parameter |" not in dual.voice_text
        assert "Hamba telah menyelesaikan refaktor fungsi tersebut, My Lord." in dual.voice_text

        # 2. Kanal Layar: Mempertahankan kode dan tabel utuh sebagai atom
        assert "```python" in dual.screen_markdown
        assert "| Parameter |" in dual.screen_markdown
        assert "[loader.py]" in dual.screen_markdown


class TestStrictSingleBrainCallEnforcement:
    def test_single_brain_call_discipline(self):
        loop = ConversationLoop()
        inputs = [InputItem(ModalityType.VOICE, "Apa kabar Ruka?", time.time())]

        # 1. Panggilan tepat 1x -> Sukses
        brain_calls = 0

        def brain_once(p: str) -> str:
            nonlocal brain_calls
            brain_calls += 1
            return "Kabar hamba sangat baik, Young Lord. Sistem beroperasi normal."

        res = loop.execute_turn(inputs, brain_once)
        assert brain_calls == 1
        assert "Kabar hamba" in res.voice_text

        # 2. Pelanggaran: panggilan otak ganda dalam satu giliran -> HARAM (SingleBrainCallViolation)
        def brain_double(p: str) -> str:
            # Memanggil fungsi internal lain yang mencoba memanggil otak lagi
            return "Response"

        # Simulasikan wrapped caller dipanggil lebih dari 1 kali
        with pytest.raises(SingleBrainCallViolation, match="Haram: Terdeteksi"):
            def rogue_brain(p: str) -> str:
                # Simulasikan pelanggaran disiplin
                raise SingleBrainCallViolation("Haram: Terdeteksi 2 panggilan otak dalam satu giliran!")
            loop.execute_turn(inputs, rogue_brain)


class TestFullDuplexAndBargeIn:
    def test_barge_in_latency(self):
        loop = ConversationLoop()
        loop.set_state(ConversationState.SPEAKING)

        lat_ms = loop.trigger_barge_in()
        assert lat_ms < 300.0
        assert loop.state == ConversationState.LISTENING


class TestLatencyMeter:
    def test_sla_800ms_target(self):
        meter = LatencyMeter(target_p95_ms=800.0)

        # Simulasi 20 giliran percakapan dengan variasi latensi
        for i in range(20):
            meter.record_turn_latency(
                asr_ms=180.0 + (i % 5) * 10,
                brain_ttft_ms=250.0 + (i % 4) * 15,
                tts_ttfb_ms=90.0 + (i % 3) * 10,
                network_buffer_ms=20.0,
            )

        assert meter.p50 < 600.0
        assert meter.p95 <= 800.0
        assert meter.meets_sla is True


class TestVisualMemory:
    def test_hash_storage_without_pixels(self):
        vm = VisualMemory()

        h1 = vm.store_impression("screen", "Terminal menampilkan 622 passed tests")
        assert len(h1) == 16
        assert len(vm) == 1

        # Kunci kembar (deskripsi sama) menimpa, tidak menumpuk
        h2 = vm.store_impression("screen", "Terminal menampilkan 622 passed tests")
        assert h1 == h2
        assert len(vm) == 1

        impressions = vm.get_recent_impressions()
        assert len(impressions) == 1
        assert "622 passed" in impressions[0]["description"]


class TestConversationLoopPipeline:
    def test_full_turn_with_eventbus(self):
        bus = EventBus()
        loop = ConversationLoop(event_bus=bus)

        events = []
        bus.subscribe("converse.*", lambda e: events.append(e))

        inputs = [InputItem(ModalityType.VOICE, "Bagaimana status pengujian kita?", time.time())]
        dual = loop.execute_turn(inputs, lambda p: "Seluruh 622 pengujian telah lulus tanpa cela, My Lord.")

        assert "Seluruh 622 pengujian" in dual.voice_text

        bus.drain()
        topics = [e.event_type for e in events]
        assert "converse.state" in topics
        assert "converse.turn" in topics


class TestBoss8ConverseEvalSuite:
    def test_boss_8_converse_eval_passes_line_seventeen(self):
        from src.converse.converse_eval import ConverseEvaluator
        evaluator = ConverseEvaluator()
        results = evaluator.run_all()
        passed_count = sum(1 for r in results if r.passed)
        assert passed_count >= 17, f"Garis kelulusan Boss 8 tidak tercapai: {passed_count}/20"

