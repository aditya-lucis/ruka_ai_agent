import pytest
from src.ruka_perception.perception.types import Modality, PerceptionInput
from src.ruka_perception.perception.validation import validate_input, PerceptionValidationError, MAX_INLINE_BYTES

def test_validate_text_valid():
    inp = PerceptionInput(modality=Modality.TEXT, text="hello")
    res = validate_input(inp)
    assert res.text == "hello"

def test_validate_text_empty():
    inp = PerceptionInput(modality=Modality.TEXT, text="   ")
    with pytest.raises(PerceptionValidationError, match="kosong"):
        validate_input(inp)

def test_validate_text_with_data_rejected():
    inp = PerceptionInput(modality=Modality.TEXT, text="hello", data=b"bytes")
    with pytest.raises(PerceptionValidationError, match="bytes tak terduga"):
        validate_input(inp)

def test_validate_image_valid_inline():
    png_bytes = b"\x89PNG\r\n\x1a\n\x00\x00\x00\x00"
    inp = PerceptionInput(modality=Modality.IMAGE, mime_type="image/png", data=png_bytes)
    res = validate_input(inp)
    assert res.data == png_bytes

def test_validate_image_mismatch_magic():
    # Klaim PNG tapi isi JPEG
    jpeg_bytes = b"\xff\xd8\xff\x00\x00\x00\x00\x00\x00\x00\x00\x00"
    inp = PerceptionInput(modality=Modality.IMAGE, mime_type="image/png", data=jpeg_bytes)
    with pytest.raises(PerceptionValidationError, match="tetapi bytes terdeteksi"):
        validate_input(inp)

def test_validate_oversize():
    inp = PerceptionInput(modality=Modality.IMAGE, mime_type="image/png", data=b"0" * (MAX_INLINE_BYTES + 1))
    with pytest.raises(PerceptionValidationError, match="melebihi batas inline"):
        validate_input(inp)

def test_validate_event_with_bytes_rejected():
    inp = PerceptionInput(modality=Modality.INTERACTION_EVENT, data=b"bad")
    with pytest.raises(PerceptionValidationError, match="tidak menerima bytes"):
        validate_input(inp)
