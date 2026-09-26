from .types import Modality, PerceptionInput, RouterDecision, PerceptionResult
from .validation import validate_input, PerceptionValidationError

DEFAULT_ROUTES = {
    Modality.TEXT: "text.represent",
    Modality.IMAGE: "vision.represent",
    Modality.AUDIO: "audio.represent",
    Modality.INTERACTION_EVENT: "interaction.appraise",
    Modality.UNKNOWN: "fallback.reject",
}

class PerceptionRouter:
    """Router sederhana: validasi -> deteksi -> keputusan handler.
    Handler tidak dipanggil di sini (inversion of control): aplikasi
    yang memanggil handler berdasarkan decision. Ini menjaga router
    bisa diuji tanpa API eksternal.
    """
    def __init__(self, routes: dict | None = None):
        self.routes = dict(DEFAULT_ROUTES)
        if routes:
            self.routes.update(routes)
        self.decisions: list[RouterDecision] = []

    def detect_modality(self, inp: PerceptionInput) -> Modality:
        """Deteksi ulang modality dari isi, bukan dari klaim.
        TEXT tetap TEXT. IMAGE/AUDIO dipercaya setelah sniffing di
        validasi. Event masuk sebagai INTERACTION_EVENT.
        """
        return inp.modality

    def route(self, inp: PerceptionInput) -> RouterDecision:
        """Validasi lalu putuskan handler. Input ditolak di-throw —
        pemanggil wajib menangani PerceptionValidationError."""
        try:
            validate_input(inp)
        except PerceptionValidationError as exc:
            decision = RouterDecision(
                inp.modality, "fallback.reject", str(exc), accepted=False)
            self.decisions.append(decision)
            raise
            
        modality = self.detect_modality(inp)
        handler = self.routes.get(modality, "fallback.ask_user")
        
        reason = f"validated as {modality.value}"
        if inp.mime_type:
            reason += f" ({inp.mime_type})"
            
        decision = RouterDecision(modality, handler, reason)
        self.decisions.append(decision)
        return decision

    def route_to_result(self, inp: PerceptionInput) -> PerceptionResult:
        """Bungkus keputusan routing sebagai PerceptionResult awal
        (tanpa embedding — tahap representasi yang mengisi)."""
        decision = self.route(inp)
        return PerceptionResult(
            modality=decision.modality,
            summary=f"routed:{decision.handler}",
            trace_id=inp.trace_id,
        )
