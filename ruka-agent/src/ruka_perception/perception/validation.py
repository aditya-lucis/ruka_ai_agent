"""Validasi input persepsi — gerbang pertama sebelum bytes dipercaya.
Prinsip: klaim MIME pengirim TIDAK dipercaya. Bytes dicek magic-number,
ukuran dicek batas, dan daftar MIME dibatasi ke format yang didukung
dokumentasi resmi (September 2026):
  image : PNG, JPEG, WEBP, HEIC, HEIF
  audio : WAV, MP3, AIFF, AAC, OGG, FLAC, MPEG, M4A, L16,
          Opus, ALAW, MULAW, WebM
Batas inline (dokumen resmi): total request <= 20 MB. Paket memakai
batas lebih ketat per file agar menyisakan ruang untuk prompt.
"""
from __future__ import annotations
from .types import Modality, PerceptionInput

# --- allowlist — SEMUA entri diverifikasi ke dokumentasi resmi -------
IMAGE_MIME = {
    "image/png", "image/jpeg", "image/webp",
    "image/heic", "image/heif",
}

AUDIO_MIME = {
    "audio/wav", "audio/mp3", "audio/aiff", "audio/aac",
    "audio/ogg", "audio/flac", "audio/mpeg", "audio/m4a",
    "audio/l16", "audio/opus", "audio/alaw", "audio/mulaw",
    "audio/webm",
}

# Batas per-file: dokumentasi resmi menyebut total request 20 MB untuk
# data inline; kita menyisakan >= 4 MB ruang untuk prompt & metadata.
MAX_INLINE_BYTES = 16 * 1024 * 1024

class PerceptionValidationError(ValueError):
    """Input ditolak di gerbang. Pesan TIDAK boleh mengandung isi
    bytes — cukup alasan + ukuran + klaim MIME."""

def sniff_image_mime(data: bytes) -> str | None:
    """Deteksi format image dari magic bytes. Return None bila tidak
    dikenali. PNG/JPEG/WEBP: magic langsung; HEIC/HEIF: ftyp box."""
    if len(data) < 12:
        return None
        
    if data[:8] == b"\x89PNG\r\n\x1a\n":
        return "image/png"
    if data[:3] == b"\xff\xd8\xff":
        return "image/jpeg"
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "image/webp"
        
    if data[4:8] == b"ftyp":
        brand = data[8:12]
        if brand in (b"heic", b"heix", b"heim", b"heis"):
            return "image/heic"
        if brand in (b"mif1", b"msf1", b"hevc", b"hevx"):
            return "image/heif"
            
    return None

def sniff_audio_mime(data: bytes) -> str | None:
    """Deteksi format audio dari magic bytes (subset paling umum:
    WAV/MP3/FLAC/OGG/WEBM/AIFF). MP3 tanpa ID3 tetap terdeteksi via
    frame sync 0xFF Ex/Fx."""
    if len(data) < 12:
        return None
        
    if data[:4] == b"RIFF" and data[8:12] == b"WAVE":
        return "audio/wav"
    if data[:3] == b"ID3":
        return "audio/mp3"
    if data[:4] == b"fLaC":
        return "audio/flac"
    if data[:4] == b"OggS":
        return "audio/ogg"
        
    if data[:4] == b"RIFF" and data[8:12] == b"WebM" or data[:4] == b"\x1aE\xdf\xa3":
        # EBML header (WebM/Matroska container)
        return "audio/webm"
    if data[:4] == b"FORM" and data[8:12] == b"AIFF":
        return "audio/aiff"
        
    # MP3 raw frame sync: 11 bit pertama = 1
    if data[0] == 0xFF and (data[1] & 0xE0) == 0xE0:
        return "audio/mp3"
        
    return None

def sniff_mime(data: bytes, modality: Modality) -> str | None:
    """Sniff sesuai modality yang diklaim."""
    if modality == Modality.IMAGE:
        return sniff_image_mime(data)
    if modality == Modality.AUDIO:
        return sniff_audio_mime(data)
    return None

def validate_input(inp: PerceptionInput) -> PerceptionInput:
    """Gerbang validasi. Raise PerceptionValidationError bila ditolak.
    Aturan:
    1. TEXT: tidak boleh kosong, tidak boleh membawa data bytes.
    2. IMAGE/AUDIO: MIME klaim harus ada di allowlist; bytes (bila
       disertakan) harus lolos sniffing dan batas ukuran inline;
       bila hanya external_ref, tetap cek allowlist MIME.
    3. INTERACTION_EVENT / UNKNOWN: lolos tanpa bytes — router yang
       menangani lebih lanjut.
    """
    if inp.modality == Modality.TEXT:
        if not (inp.text and inp.text.strip()):
            raise PerceptionValidationError("TEXT ditolak: teks kosong")
        if inp.data:
            raise PerceptionValidationError(
                "TEXT ditolak: membawa bytes tak terduga")
        return inp
        
    if inp.modality in (Modality.IMAGE, Modality.AUDIO):
        allow = IMAGE_MIME if inp.modality == Modality.IMAGE else AUDIO_MIME
        if not inp.mime_type:
            raise PerceptionValidationError(
                f"{inp.modality.value} ditolak: mime_type wajib diisi")
        if inp.mime_type not in allow:
            raise PerceptionValidationError(
                f"{inp.modality.value} ditolak: mime '{inp.mime_type}' "
                f"bukan format yang didukung")
                
        if inp.data is not None:
            if len(inp.data) > MAX_INLINE_BYTES:
                raise PerceptionValidationError(
                    f"{inp.modality.value} ditolak: {len(inp.data)} bytes "
                    f"melebihi batas inline {MAX_INLINE_BYTES}")
            
            real = sniff_mime(inp.data, inp.modality)
            if real is None:
                raise PerceptionValidationError(
                    f"{inp.modality.value} ditolak: magic bytes tidak "
                    f"dikenali sebagai {inp.mime_type}")
            if real != inp.mime_type:
                raise PerceptionValidationError(
                    f"{inp.modality.value} ditolak: klaim {inp.mime_type} "
                    f"tetapi bytes terdeteksi {real}")
        elif not inp.external_ref:
            raise PerceptionValidationError(
                f"{inp.modality.value} ditolak: tanpa bytes dan tanpa "
                f"external_ref tidak ada yang bisa diproses")
                
        return inp
        
    # INTERACTION_EVENT, UNKNOWN: tanpa bytes
    if inp.data:
        raise PerceptionValidationError(
            f"{inp.modality.value} ditolak: tidak menerima bytes")
            
    return inp
