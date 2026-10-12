# -*- coding: utf-8 -*-
"""Uji U0.4: StandaloneBrainFallback di launcher dan Gateway.
Memastikan saat brain/kognisi gagal init atau tidak siap:
- Tidak menghasilkan jawaban companion/agentic palsu seolah Marquis penuh.
- Tidak menghasilkan kode palsu (python/powershell/excel).
- Tidak menghasilkan memori palsu.
- Menghasilkan pesan jujur singkat kognisi tidak siap.
- Path normal think_and_reply tidak diubah saat brain sehat.
"""
from __future__ import annotations

import json
from pathlib import Path
import pytest
import launcher
from src.gateway import RukaGatewayServer
from src.gateway.protocol import InboundMessage


class DummyHealthyBrain:
    def __init__(self):
        self.called_with = []

    def think_and_reply(self, text: str, attachment=None) -> str:
        self.called_with.append((text, attachment))
        return f"Jawaban kognitif asli Marquis: {text}"


def test_launcher_fallback_when_brain_unready(tmp_path: Path):
    """Saat brain None / kognisi gagal init, launcher harus pesan jujur singkat."""
    srv = launcher.RukaBrainServer(workspace=tmp_path)
    srv.brain = None
    srv.brain_init_error = "Simulasi kognisi gagal init"

    test_prompts = [
        "halo ruka",
        "tolong buat koding python untuk monitor cpu",
        "jalankan perintah cli powershell",
        "buat rumus excel vlookup",
        "siapa kamu sebenarnya?",
        "ingatan dan memori apa yang tersimpan?",
        "analisis proyek ini dan jalankan terminal",
    ]

    for p in test_prompts:
        req = {
            "channel": "ruka:chat-send",
            "correlationId": f"test-{hash(p)}",
            "protocolVersion": 2,
            "payload": {"text": p},
        }
        resp, _ = srv._process_request(req, is_auth=True)
        assert resp is not None
        assert resp["type"] == "response"
        delta = resp["payload"]["delta"]

        # Harus berisi pesan jujur kognisi tidak siap
        assert "[Kognisi Tidak Siap]" in delta
        assert "Simulasi kognisi gagal init" in delta

        # Dilarang: nalar palsu, kode palsu, pura-pura skills, persona kemenangan palsu
        assert "permainan cakar" not in delta
        assert "```python" not in delta
        assert "```powershell" not in delta
        assert "```excel" not in delta
        assert "Seluruh nalar kognisi Ruka siap melayani instruksi Anda" not in delta
        assert "telah terindeks ke dalam cakar nalar saya" not in delta


def test_launcher_memory_search_fallback_honest(tmp_path: Path):
    """Saat brain None, memory-search tidak boleh menghasilkan mock ingatan palsu."""
    srv = launcher.RukaBrainServer(workspace=tmp_path)
    srv.brain = None

    req = {
        "channel": "ruka:memory-search",
        "correlationId": "test-mem-1",
        "protocolVersion": 2,
        "payload": {"query": "doktrin zero trust"},
    }
    resp, _ = srv._process_request(req, is_auth=True)
    assert resp is not None
    assert resp["type"] == "response"
    hits = resp["payload"]["hits"]
    # Tidak boleh ada mock memory "426 uji klinis Volume VI lulus 100%"
    assert hits == []


def test_launcher_healthy_brain_path_untouched(tmp_path: Path):
    """Saat brain sehat, path normal think_and_reply harus berjalan tanpa diubah."""
    srv = launcher.RukaBrainServer(workspace=tmp_path)
    dummy_brain = DummyHealthyBrain()
    srv.brain = dummy_brain

    req = {
        "channel": "ruka:chat-send",
        "correlationId": "test-healthy-1",
        "protocolVersion": 2,
        "payload": {"text": "Uji kognisi sehat"},
    }
    resp, _ = srv._process_request(req, is_auth=True)
    assert resp is not None
    assert resp["type"] == "response"
    delta = resp["payload"]["delta"]

    # Harus berasal dari brain.think_and_reply normal
    assert "Jawaban kognitif asli Marquis: Uji kognisi sehat" in delta
    assert "[Kognisi Tidak Siap]" not in delta
    assert len(dummy_brain.called_with) == 1
    assert dummy_brain.called_with[0][0] == "Uji kognisi sehat"


def test_gateway_chat_fallback_honest():
    """Saat gateway tidak memiliki brain, harus memberi pesan jujur singkat."""
    gw = RukaGatewayServer(brain=None)
    msg = InboundMessage(
        type="request",
        channel="desktop",
        session_id="test_sess",
        content={"text": "Halo Ruka"},
        metadata={"ipc_channel": "ruka:chat-send"},
    )
    resp = gw.dispatch_inbound(msg)
    assert resp is not None
    delta = resp.content.get("delta", "")
    assert "[Kognisi Tidak Siap]" in delta
    assert "Nalar dan eksekusi skills tidak aktif" in delta
    assert "mendengar titah" not in delta
