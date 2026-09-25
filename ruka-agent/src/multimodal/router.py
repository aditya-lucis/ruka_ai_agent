"""Multimodal router — normalisasi input & kebijakan modality.
API terverifikasi (dok. resmi, Sep 2026):
- upload:    client.files.upload(file=path) -> {uri, mime_type}
- input:     input=[{"type":"text",...}, {"type":"image",
             "uri":..., "mime_type":...}]  (juga "type":"audio")
- multimodal function calling: function_result boleh memuat
  {"type":"image", "data": base64, "mime_type": "image/png"}
"""
from __future__ import annotations
import base64
import mimetypes
from dataclasses import dataclass
from enum import Enum
from pathlib import Path

class Modality(str, Enum):
    TEXT = "text"
    IMAGE = "image"
    AUDIO = "audio"

# Kebijakan: bukan semua file layak naik. Pagar ukuran & tipe.
MAX_IMAGE_BYTES = 4 * 1024 * 1024        # 4 MB
MAX_AUDIO_BYTES = 15 * 1024 * 1024       # 15 MB
ALLOWED_IMAGE_MIMES = {"image/png", "image/jpeg", "image/webp"}
ALLOWED_AUDIO_MIMES = {"audio/mpeg", "audio/wav", "audio/ogg",
                        "audio/webm", "audio/mp4", "audio/aac"}

class ModalityPolicyError(ValueError):
    """File melanggar kebijakan modality — ditolak dengan alasan."""

@dataclass(frozen=True)
class ModalityDecision:
    accepted: bool
    reason: str = ""

class MultimodalRouter:
    """Satu-satunya tempat modality ditimbang sebelum naik ke LLM."""
    def __init__(self, client) -> None:      # client: genai.Client
        self._client = client

    def check_file(self, path: Path) -> ModalityDecision:
        if not path.exists():
            return ModalityDecision(False, f"file tidak ada: {path}")
        mime, _ = mimetypes.guess_type(path.name)
        size = path.stat().st_size
        if mime in ALLOWED_IMAGE_MIMES:
            if size > MAX_IMAGE_BYTES:
                return ModalityDecision(False, "gambar > 4 MB")
            return ModalityDecision(True, "image")
        if mime in ALLOWED_AUDIO_MIMES:
            if size > MAX_AUDIO_BYTES:
                return ModalityDecision(False, "audio > 15 MB")
            return ModalityDecision(True, "audio")
        return ModalityDecision(False, f"tipe tidak didukung: {mime}")

    def build_input(self, text: str, attachments: list[Path]) -> list[dict]:
        """Teks + lampiran -> daftar part Interactions (stateless Vol I).
        Upload via Files API; URI dipakai di part (bukan base64 besar)
        supaya payload request tetap ramping dan cacheable."""
        parts: list[dict] = [{"type": "text", "text": text}]
        for att in attachments:
            decision = self.check_file(att)
            if not decision.accepted:
                raise ModalityPolicyError(
                    f"{att.name} ditolak router: {decision.reason}")
            uploaded = self._client.files.upload(file=str(att))
            mtype = "image" if decision.reason == "image" else "audio"
            parts.append({"type": mtype,
                          "uri": uploaded.uri,
                          "mime_type": uploaded.mime_type})
        return parts

    @staticmethod
    def tool_image_part(path: Path) -> dict:
        """Multimodal function calling: kembalikan GAMBAR sebagai
        function_result part (data base64 inline, terverifikasi)."""
        mime, _ = mimetypes.guess_type(path.name)
        if mime not in ALLOWED_IMAGE_MIMES:
            raise ModalityPolicyError(f"bukan gambar yang didukung: {mime}")
        data = base64.b64encode(path.read_bytes()).decode("ascii")
        return {"type": "image", "data": data, "mime_type": mime}

SCREENDIAG_TOOL = {
    "type": "function",
    "name": "read_screenshot",
    "description": ("Membaca berkas tangkapan layar dan mengembalikannya "
                     "sebagai gambar untuk dianalisis model."),
    "parameters": {
        "type": "object",
        "properties": {
            "path": {"type": "string",
                      "description": "path file tangkapan layar"}
        },
        "required": ["path"],
    },
}
