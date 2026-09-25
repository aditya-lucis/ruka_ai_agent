from __future__ import annotations
import asyncio
from unittest.mock import AsyncMock, MagicMock
import pytest
from google.genai import types
from src.capability.registry import default_registry
from src.multimodal.live import (
    LiveLimits,
    LiveRuntimeState,
    LiveSession,
    LiveSessionManager,
)

def test_legacy_transcript_attribute_does_not_exist():
    """Membuktikan bug KI-02: LiveServerMessage SDK ASLI tidak punya 'transcript'."""
    msg = types.LiveServerMessage()
    assert not hasattr(msg, "transcript")
    with pytest.raises(AttributeError):
        _ = getattr(msg, "transcript_does_not_exist_xyz")

def test_transcript_arrives_via_server_content():
    """FIX KI-02: transkrip tiba via server_content.input_transcription.text."""
    session = LiveSession(
        client=MagicMock(),
        live_model="gemini-3.1-flash-live-preview",
        system_instruction="sys",
        registry=default_registry(),
    )
    transcripts = []
    msg = types.LiveServerMessage(
        server_content=types.LiveServerContent(
            input_transcription=types.Transcription(text="Halo Ruka")
        )
    )
    session._dispatch(msg, on_audio=lambda b: None, on_transcript=transcripts.append)
    assert transcripts == ["Halo Ruka"]
    assert session.state.received_transcripts == 1

def test_audio_dispatched():
    session = LiveSession(
        client=MagicMock(),
        live_model="gemini-3.1-flash-live-preview",
        system_instruction="sys",
        registry=default_registry(),
    )
    audio_chunks = []
    msg = types.LiveServerMessage(
        server_content=types.LiveServerContent(
            model_turn=types.Content(
                parts=[
                    types.Part(
                        inline_data=types.Blob(
                            data=b"\x01\x02", mime_type="audio/pcm;rate=24000"
                        )
                    )
                ]
            )
        )
    )
    session._dispatch(msg, on_audio=audio_chunks.append, on_transcript=lambda t: None)
    assert audio_chunks == [b"\x01\x02"]
    assert session.state.received_audio_chunks == 1

def test_interrupted_signals_playback_stop():
    """FIX KI-08: interrupted mengirim b'' ke audio callback."""
    session = LiveSession(
        client=MagicMock(),
        live_model="gemini-3.1-flash-live-preview",
        system_instruction="sys",
        registry=default_registry(),
    )
    audio_chunks = []
    msg = types.LiveServerMessage(
        server_content=types.LiveServerContent(interrupted=True)
    )
    session._dispatch(msg, on_audio=audio_chunks.append, on_transcript=lambda t: None)
    assert audio_chunks == [b""]
    assert session.state.interrupted == 1

def test_go_away_recorded_with_time_left():
    """FIX KI-04: go_away dicatat dengan peringatan."""
    session = LiveSession(
        client=MagicMock(),
        live_model="gemini-3.1-flash-live-preview",
        system_instruction="sys",
        registry=default_registry(),
    )
    msg = types.LiveServerMessage(
        go_away=types.LiveServerGoAway(time_left="60s")
    )
    session._dispatch(msg, on_audio=lambda b: None, on_transcript=lambda t: None)
    assert session.state.go_away_seen is True
    assert len(session.state.warnings) == 1
    assert "60s" in session.state.warnings[0]

def test_resumption_handle_harvested():
    """FIX KI-04: session_resumption_update memanen handle."""
    session = LiveSession(
        client=MagicMock(),
        live_model="gemini-3.1-flash-live-preview",
        system_instruction="sys",
        registry=default_registry(),
    )
    msg = types.LiveServerMessage(
        session_resumption_update=types.LiveServerSessionResumptionUpdate(
            new_handle="resume-token-xyz"
        )
    )
    session._dispatch(msg, on_audio=lambda b: None, on_transcript=lambda t: None)
    assert session.state.last_resumption_handle == "resume-token-xyz"

def test_generation_complete_handled():
    session = LiveSession(
        client=MagicMock(),
        live_model="gemini-3.1-flash-live-preview",
        system_instruction="sys",
        registry=default_registry(),
    )
    msg = types.LiveServerMessage(
        server_content=types.LiveServerContent(generation_complete=True)
    )
    session._dispatch(msg, on_audio=lambda b: None, on_transcript=lambda t: None)

def test_build_config_sets_resumption_handle():
    session = LiveSession(
        client=MagicMock(),
        live_model="gemini-3.1-flash-live-preview",
        system_instruction="sys",
        registry=default_registry(),
    )
    cfg = session._build_config(resumption_handle="handle-123")
    assert cfg.session_resumption.handle == "handle-123"

def test_build_config_sets_compression_and_thinking():
    session = LiveSession(
        client=MagicMock(),
        live_model="gemini-3.1-flash-live-preview",
        system_instruction="sys",
        registry=default_registry(),
    )
    cfg = session._build_config(resumption_handle=None)
    assert cfg.context_window_compression is not None
    assert str(cfg.thinking_config.thinking_level).lower().endswith("low")

def test_pump_mic_sends_no_empty_blob():
    """FIX KI-05: tidak ada empty blob di akhir mic stream."""
    async def run():
        session_mock = MagicMock()
        session_mock.send_realtime_input = AsyncMock()

        async def mic():
            yield b"\x01\x02"
            yield b"\x03\x04"

        await LiveSession._pump_mic(session_mock, mic())
        calls = session_mock.send_realtime_input.call_args_list
        assert len(calls) == 2
        for c in calls:
            blob = c.kwargs["audio"]
            assert len(blob.data) > 0

    asyncio.run(run())

def test_live_session_manager_init():
    mgr = LiveSessionManager(
        client=MagicMock(),
        live_model="gemini-3.1-flash-live-preview",
        registry=default_registry(),
        limits=LiveLimits(reconnect_budget=5),
    )
    assert mgr._limits.reconnect_budget == 5

def test_manager_reconnect_budget_and_state(monkeypatch):
    """Manager mencoba hingga reconnect_budget dan berhenti terhormat."""
    async def run():
        mgr = LiveSessionManager(
            client=MagicMock(),
            live_model="gemini-3.1-flash-live-preview",
            registry=default_registry(),
            limits=LiveLimits(reconnect_budget=2, backoff_base=0.0),
        )

        async def fail_run(*args, **kwargs):
            raise ConnectionError("websocket broken")

        monkeypatch.setattr(LiveSession, "run", fail_run)

        async def mic_gen():
            yield b""

        state = await mgr.converse(
            system_instruction="sys",
            mic_chunks_factory=mic_gen,
            on_audio=lambda b: None,
            on_transcript=lambda t: None,
        )
        assert state.reconnects >= 2

    asyncio.run(run())

def test_manager_handles_cancellation_loudly(monkeypatch):
    async def run():
        mgr = LiveSessionManager(
            client=MagicMock(),
            live_model="gemini-3.1-flash-live-preview",
            registry=default_registry(),
            limits=LiveLimits(backoff_base=0.0),
        )

        async def cancel_run(*args, **kwargs):
            raise asyncio.CancelledError()

        monkeypatch.setattr(LiveSession, "run", cancel_run)

        async def mic_gen():
            yield b""

        with pytest.raises(asyncio.CancelledError):
            await mgr.converse(
                system_instruction="sys",
                mic_chunks_factory=mic_gen,
                on_audio=lambda b: None,
                on_transcript=lambda t: None,
            )

    asyncio.run(run())

def test_manager_converse_success(monkeypatch):
    async def run():
        mgr = LiveSessionManager(
            client=MagicMock(),
            live_model="gemini-3.1-flash-live-preview",
            registry=default_registry(),
        )

        async def success_run(*args, **kwargs):
            return

        monkeypatch.setattr(LiveSession, "run", success_run)

        async def mic_gen():
            yield b""

        state = await mgr.converse(
            system_instruction="sys",
            mic_chunks_factory=mic_gen,
            on_audio=lambda b: None,
            on_transcript=lambda t: None,
        )
        assert isinstance(state, LiveRuntimeState)
        assert state.reconnects == 0

    asyncio.run(run())
