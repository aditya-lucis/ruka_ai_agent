"""Score fusion and fusion strategy policy for Ruka Perception — multimodal module.

Implements Listings 8.2 and 8.3 from RUKA-IV Part VIII.
Rule-based fusion policy: cheapest strategy that is adequate.
"""

from __future__ import annotations


# ---------------------------------------------------------------------------
# Listing 8.2 — ScoreFusion + deteksi modality hilang (Part VIII)
# ---------------------------------------------------------------------------

class ScoreFusion:
    """Score-based fusion: rata-rata terbobot skor per modality.

    Skor harus KOMPARABEL (sudah dinormalkan ke [0,1] oleh pemanggil —
    modul menolak rentang liar). Bobot wajib berjumlah 1 supaya hasil
    tetap di [0,1]. Ini kandidat fusion paling murah dan paling bisa
    dijelaskan — baseline WAJIB sebelum fusion neural.
    """

    def __init__(self, weights: dict[str, float]) -> None:
        total = sum(weights.values())
        if total <= 0:
            raise ValueError("total bobot harus > 0")
        self.weights = {k: v / total for k, v in weights.items()}

    def fuse(self, scores: dict[str, float]) -> float:
        """Gabung skor per modality.

        Modality tanpa bobot diabaikan (dan dilaporkan lewat missing()).
        Skor di luar [0,1] DITOLAK — membandingkan log-likelihood mentah
        dengan probabilitas adalah bug satuan.
        """
        out, used = 0.0, []
        for name, w in self.weights.items():
            if name in scores:
                s = float(scores[name])
                if not (0.0 <= s <= 1.0):
                    raise ValueError(
                        f"skor {name}={s} di luar [0,1] — normalkan dulu"
                    )
                out += w * s
                used.append(name)
        if not used:
            raise ValueError("tidak ada skor yang cocok dengan bobot")
        return out

    def missing(self, scores: dict[str, float]) -> list[str]:
        """Modality berbobot tapi tak tersedia.

        Dipakai untuk menurunkan kepercayaan hasil fusion, bukan untuk gagal total.
        """
        return [k for k in self.weights if k not in scores]


# ---------------------------------------------------------------------------
# Listing 8.3 — Kebijakan hybrid fusion: termurah yang memadai (Part VIII)
# ---------------------------------------------------------------------------

def choose_fusion_strategy(
    available: list[str],
    latency_budget_ms: float,
    interaction_needs_cross_modal: bool = True,
) -> str:
    """Kebijakan hybrid: pilih fusion termurah yang memadai.

    Aturan (urut kebutuhan):
      1. satu modality saja      -> 'single' (tidak perlu fusion)
      2. butuh keputusan cepat   -> 'score' (rata-rata terbobot)
      3. ranking kandidat banyak -> 'late'  (Borda)
      4. butuh interaksi token   -> 'early' / 'cross_attention'

    Rule-based BY DESIGN — keputusan arsitektur yang bisa dijelaskan
    lebih dulu, neural fusion belakangan (Vol III Part VI memberikan
    kerangka 9 pertanyaan sebelum memakai model).
    """
    if len(available) <= 1:
        return "single"
    if not interaction_needs_cross_modal:
        return "score" if latency_budget_ms < 400 else "late"
    return "cross_attention" if latency_budget_ms >= 400 else "early"


def late_fusion_borda(
    rankings: dict[str, list[str]],
) -> list[str]:
    """Late fusion dengan Borda count.

    rankings: {modality: [kandidat terbaik ke terburuk]}
    Return: kandidat diurutkan dari skor Borda tertinggi.
    """
    scores: dict[str, float] = {}
    for modality, rank_list in rankings.items():
        n = len(rank_list)
        for i, candidate in enumerate(rank_list):
            scores[candidate] = scores.get(candidate, 0.0) + (n - i)
    return sorted(scores, key=lambda c: scores[c], reverse=True)
