"""Voice output — TTS via Interactions API (terverifikasi).
Model:  gemini-3.1-flash-tts-preview (preview publik Apr 2026)
Output: interaction.output_audio.data -> base64 PCM 24kHz/16bit/mono
Suara:  30 pilihan; Indonesian didukung; default Ruka = Sulafat
Gaya:   petunjuk natural + audio tags; TIDAK ada parameter emosi
"""
from __future__ import annotations
import base64
import wave
from pathlib import Path
from google import genai
from src.config import Settings

SAMPLE_RATE = 24_000                 # output TTS (dok. resmi)
SAMPLE_WIDTH = 2                    # 16-bit
CHANNELS = 1

# Kartu suara Ruka — padanan AUDIO PROFILE dari dok. prompting:
# nama persona, scene ringkas, director's notes (style/pacing/accent).
# Inilah “siapa Ruka” di dunia audio; identik dengan PART 3.
RUKA_VOICE_PROFILE = """# AUDIO PROFILE: Ruka, Marquis Trendamis
## THE SCENE: Ruang kerja hangat menjelang tengah malam; lampu meja
emas; kucing vampir berjubah duduk tegak namun santai.
### DIRECTOR'S NOTES
Style: aristokrat tenang; hangat pada Bos; humor kering tipis.
Pacing: terukur, tidak tergesa; jeda pendek sebelum poin penting.
Accent: netral internasional, sentuhan formal ringan.
#### TRANSCRIPT
"""

class VoiceOut:
    def __init__(self, client: genai.Client, settings: Settings) -> None:
        self._client = client
        self._settings = settings

    def speak(self, text: str, tone_hint: str = "calm, neutral",
              out_path: Path | None = None) -> Path:
        """Teks -> WAV. tone_hint dari expression engine (PART 6)."""
        styled = (
            f"{RUKA_VOICE_PROFILE}"
            f"Read the transcript below in a tone that is {tone_hint}.\n"
            f"{text}"
        )
        interaction = self._client.interactions.create(
            model=self._settings.tts_model,
            input=styled,
            response_format={"type": "audio"},
            generation_config={
                "speech_config": [{"voice": self._settings.voice}],
            },
        )
        pcm = base64.b64decode(interaction.output_audio.data)
        out_path = out_path or Path("data/voice") / "ruka_last.wav"
        out_path.parent.mkdir(parents=True, exist_ok=True)
        _write_wav(out_path, pcm)
        return out_path

def _write_wav(path: Path, pcm: bytes) -> None:
    with wave.open(str(path), "wb") as wf:
        wf.setnchannels(CHANNELS)
        wf.setsampwidth(SAMPLE_WIDTH)
        wf.setframerate(SAMPLE_RATE)
        wf.writeframes(pcm)
