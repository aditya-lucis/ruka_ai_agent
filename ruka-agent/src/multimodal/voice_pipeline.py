"""Pipeline suara batch: STT -> agent -> ekspresi -> TTS.
STT terverifikasi: files.upload + part {type: audio, uri, mime_type}
ke model utama (gemini-3.8-flash) dengan instruksi transkripsi.
"""
from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
from google import genai
from src.config import Settings
from src.multimodal.voice_out import VoiceOut

@dataclass
class TurnResult:
    transcript: str
    answer: str
    wav_path: Path
    tone_used: str

class VoicePipeline:
    def __init__(self, client: genai.Client, settings: Settings,
                 agent, expression) -> None:
        """agent: orkestrator Vol I (dengan budget PART 13);
        expression: ExpressionEngine PART 6 (memberi tone_hint)."""
        self._client = client
        self._settings = settings
        self._agent = agent
        self._expression = expression
        self._voice = VoiceOut(client, settings)

    def transcribe(self, audio_path: Path) -> str:
        uploaded = self._client.files.upload(file=str(audio_path))
        interaction = self._client.interactions.create(
            model=self._settings.model,
            input=[
                {"type": "text",
                 "text": ("Transkripsikan audio ini apa adanya. "
                          "Kembalikan hanya transkrip, tanpa komentar.")},
                {"type": "audio",
                 "uri": uploaded.uri,
                 "mime_type": uploaded.mime_type},
            ],
            store=False,
        )
        return (interaction.output_text or "").strip()

    def run_turn(self, audio_path: Path) -> TurnResult:
        """Satu giliran penuh suara -> suara."""
        transcript = self.transcribe(audio_path)
        answer = self._agent.run(transcript)          # jalur normal,
                                                        # lengkap dgn tools
        params = self._expression.decide(phase="responding")
        wav = self._voice.speak(answer, tone_hint=params.voice_tone)
        return TurnResult(transcript=transcript, answer=answer,
                          wav_path=wav, tone_used=params.voice_tone)
