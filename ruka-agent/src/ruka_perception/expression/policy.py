"""Expression Policy and Honesty Guard for Ruka Perception.

Implements Listings 12.2 and 12.3 from RUKA-IV.
Separates PERSONA MASK (styling) from HONESTY GUARD (factual integrity).
Protected message kinds are ALWAYS sent verbatim — no softening.
"""

from __future__ import annotations

from .state import ExpressionState, STATE_DIMS
import numpy as np


class HonestyGuard:
    """Penjaga kejujuran ekspresi: gaya boleh berubah, fakta tidak."""

    # Jenis pesan yang TIDAK BOLEH di-mute oleh persona mask.
    PROTECTED = {"error_disclosure", "capability_limit", "uncertainty", "security_warning"}

    def check(self, message: dict) -> bool:
        """True = pesan ini BOLEH dimask (gaya). False = harus disampaikan apa adanya.

        message minimal punya 'kind'.
        """
        return message.get("kind", "") not in self.PROTECTED


class ExpressionPolicy:
    """Peta ExpressionState -> gaya eksternal.

    Output policy (bukan hanya satu string):
      - text_style   : petunjuk tone untuk LLM persona
      - voice_style  : petunjuk gaya untuk TTS (tag audio resmi
        seperti [whispers] / [shouting] — dokumen Vol II)
      - avatar_label : label ekspresi avatar (via state)
    """

    # persona mask: Ruka sok dingin — concern tidak diteriakkan
    PERSONA_SOFTENING = {
        "concern": 0.6,       # concern dikaburkan 40% di teks
        "confidence": 0.85,   # sombong sedikit dikurangi
        "playfulness": 1.0,   # gemesin dibiarkan apa adanya
    }

    def __init__(self, honesty: HonestyGuard | None = None) -> None:
        self.honesty = honesty or HonestyGuard()

    def text_style(self, state: ExpressionState) -> dict:
        """Petunjuk gaya teks. concern di-mask (persona), tetapi
        tetap dilaporkan di field 'masked_cue' supaya audit bisa
        melihat bahwa kejujuran diserahkan ke TULISAN pesan
        sebenarnya, bukan ke tone.
        """
        s = state.s
        softened = {
            d: float(s[i] * self.PERSONA_SOFTENING.get(d, 1.0))
            for i, d in enumerate(STATE_DIMS)
        }
        # masked_cue: perbedaan concern aktual vs yang ditampilkan
        masked_cue = {
            "concern_actual": float(s[STATE_DIMS.index("concern")]),
            "concern_shown": softened["concern"],
        }
        return {
            "tone": state.dominant(),
            "softened": softened,
            "masked_cue": masked_cue,
        }

    def voice_style(self, state: ExpressionState) -> dict:
        """Petunjuk gaya TTS berdasarkan state.

        Tag audio resmi TTS Vol II: [whispers], [shouting], dll.
        Concern tinggi mengarah ke tone lebih serius/hati-hati.
        """
        s = state.s
        concern = float(s[STATE_DIMS.index("concern")])
        playfulness = float(s[STATE_DIMS.index("playfulness")])
        calm = float(s[STATE_DIMS.index("calm")])

        if concern > 0.6:
            tag = "[hesitant]"
        elif playfulness > 0.65:
            tag = "[excited]"
        elif calm > 0.85:
            tag = "[calm]"
        else:
            tag = ""  # tone default TTS

        return {"audio_tag": tag, "concern_level": concern}

    def avatar_style(self, state: ExpressionState) -> dict:
        """Label avatar dan intensitas untuk AvatarMapper Part XIII."""
        label = state.to_avatar_label()
        rel = state.s - state.baseline
        intensity = float(max(rel.max(), 0.0))
        return {"label": label, "intensity": intensity}

    def express(self, state: ExpressionState, message: dict) -> dict:
        """Kebijakan penuh untuk SATU pesan keluar.

        message = {'kind': ..., 'text': ...}. Bila kind masuk daftar
        dilindungi HonestyGuard, petunjuk 'verbatim' = True:
        pesan harus dikirim tanpa softening — pipeline pesan
        (ruka-agent) bertanggung jawab mematikan mask.
        """
        verbatim = not self.honesty.check(message)
        return {
            "verbatim": verbatim,
            "text_style": self.text_style(state),
            "voice_style": self.voice_style(state),
            "avatar_style": self.avatar_style(state),
        }
