"""Avatar Mapper — Crimson Presence L0/L1 untuk Ruka.

Implements Listing 13.1 from RUKA-IV Part XIII.

Mapper memetakan label ekspresi + intensitas → aset statis & hint blend.
Identitas TERKUNCI ke referensi karakter; variasi hanya ekspresi di atasnya.
"""

from __future__ import annotations

from ruka_perception.companion.continuity import LABEL_SEQUENCE

# Label dasar dari ExpressionState.to_avatar_label()
AVATAR_LABELS = {"calm", "curious", "concerned", "playful", "confident", "neutral"}

# Label tambahan yang mungkin muncul dari domain khusus
EXTENDED_LABELS = {"proud", "focused", "hesitant", "embarrassed"}


class AvatarMapper:
    """Mapper L0/L1: label + intensitas -> aset statis & hint blend.

    aset() mengembalikan PATH KONSEPTUAL (kontrak), bukan file nyata —
    pasangan path/aset di-bind oleh aplikasi lewat asset_dir. Ini
    menjaga paket tetap murni logic dan bisa diuji tanpa file gambar.
    """

    def __init__(
        self,
        asset_dir: str = "assets/avatar",
        blend_threshold: float = 0.35,
    ) -> None:
        if blend_threshold <= 0 or blend_threshold >= 1:
            raise ValueError("blend_threshold di (0,1)")
        self.asset_dir = asset_dir.rstrip("/")
        self.blend_threshold = blend_threshold

    def asset_path(self, label: str) -> str:
        """Path aset untuk label.

        Label tak dikenal -> neutral (fallback eksplisit, bukan exception:
        avatar rusak tidak boleh menjatuhkan seluruh interaksi).
        """
        if label not in AVATAR_LABELS and label not in EXTENDED_LABELS:
            label = "neutral"
        return f"{self.asset_dir}/{label}.png"

    def plan(self, label: str, intensity: float) -> dict:
        """Rencana render untuk satu update ekspresi.

        intensity < blend_threshold : tetap 'neutral' — menghindari
            avatar menari pada mikro-perubahan (kebisingan state).
        intensity >= blend_threshold: pakai label target.
        blend_ms: durasi cross-fade L1 (0 = potong langsung).
        """
        if not (0.0 <= intensity <= 1.0):
            raise ValueError("intensity di [0,1]")
        active = label if intensity >= self.blend_threshold else "neutral"
        return {
            "from": "previous",
            "to": self.asset_path(active),
            "label": active,
            "blend_ms": 180 if active != "neutral" else 0,
            "render_tier": "L1_blend",
        }

    def continuity_rule(self, prev_label: str, next_label: str) -> bool:
        """Aturan kontinuitas Part XIV: transisi ekspresi harus punya SEBAB.

        Mapper hanya memvalidasi jarak tetangga pada kosakata KANONIK
        (LABEL_SEQUENCE — sama dengan companion.continuity): transisi
        melompat > 2 langkah dianggap curiga dan perlu ditinjau (bukan
        diblokir — validator continuity yang memutuskan dengan konteks).
        """
        try:
            d = abs(
                LABEL_SEQUENCE.index(prev_label)
                - LABEL_SEQUENCE.index(next_label)
            )
        except ValueError:
            return True  # label asing: lewatkan
        return d <= 2
