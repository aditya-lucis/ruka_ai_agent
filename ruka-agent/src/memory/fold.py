from src.llm.structured import ask_structured
from src.memory.models import SessionSummary

def fold_history(client, old_messages: list[str],
                 keep_recent: int = 6) -> SessionSummary:
    """Lipat pesan lama jadi ringkasan; pertahankan N terakhir."""
    transcript = "\n".join(old_messages[:-keep_recent])
    return ask_structured(
        client,
        f"Ringkas percakapan berikut, pertahankan fakta, "
        f"keputusan, dan preferensi:\n{transcript}",
        SessionSummary,
    )
