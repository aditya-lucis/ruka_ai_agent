import base64
import wave
from pathlib import Path
import pytest
from src.multimodal.voice_out import (_write_wav, CHANNELS,
                                      SAMPLE_RATE, SAMPLE_WIDTH,
                                      RUKA_VOICE_PROFILE)

class FakeOutputAudio:
    def __init__(self, pcm: bytes):
        self.data = base64.b64encode(pcm).decode("ascii")

class FakeInteraction:
    def __init__(self, pcm: bytes):
        self.output_audio = FakeOutputAudio(pcm)

class FakeClient:
    def __init__(self, pcm: bytes):
        self._pcm = pcm
        self.calls: list[dict] = []

    @property
    def interactions(self):
        client = self
        class _I:
            def create(self, **kwargs):
                client.calls.append(kwargs)
                return FakeInteraction(client._pcm)
        return _I()

class FakeSettings:
    tts_model = "gemini-3.1-flash-tts-preview"
    voice = "Sulafat"
    model = "gemini-3.8-flash"

def test_speak_writes_valid_wav(tmp_path: Path):
    from src.multimodal.voice_out import VoiceOut
    pcm = b"\x00\x01" * 12000                     # 12000 sampel 16-bit
    out = VoiceOut(FakeClient(pcm), FakeSettings()).speak(
        "Yes, Sir!", out_path=tmp_path / "t.wav")
    with wave.open(str(out), "rb") as wf:
        assert wf.getframerate() == SAMPLE_RATE == 24_000
        assert wf.getsampwidth() == SAMPLE_WIDTH == 2
        assert wf.getnchannels() == CHANNELS == 1
        assert wf.getnframes() == 12000

def test_speak_sends_verified_shape(tmp_path: Path):
    from src.multimodal.voice_out import VoiceOut
    client = FakeClient(b"")
    VoiceOut(client, FakeSettings()).speak("halo",
                                          out_path=tmp_path / "t.wav")
    call = client.calls[0]
    assert call["model"] == "gemini-3.1-flash-tts-preview"
    assert call["response_format"] == {"type": "audio"}
    assert call["generation_config"]["speech_config"] == [
        {"voice": "Sulafat"}]
    assert RUKA_VOICE_PROFILE in call["input"]      # kartu suara ikut
    assert "halo" in call["input"]
