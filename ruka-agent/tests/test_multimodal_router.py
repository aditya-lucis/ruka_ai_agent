from pathlib import Path
import pytest
from src.multimodal.router import (ModalityPolicyError,
                                    MultimodalRouter)

class FakeUpload:
    def __init__(self, uri: str, mime_type: str):
        self.uri, self.mime_type = uri, mime_type

class FakeFiles:
    def __init__(self):
        self.uploaded: list[str] = []

    def upload(self, file: str) -> FakeUpload:
        self.uploaded.append(file)
        name = Path(file).name
        mime = "image/png" if name.endswith(".png") else "audio/mpeg"
        return FakeUpload(f"files/fake-{len(self.uploaded)}", mime)

class FakeClient:
    def __init__(self):
        self.files = FakeFiles()

@pytest.fixture()
def png(tmp_path: Path) -> Path:
    p = tmp_path / "shot.png"
    p.write_bytes(b"\x89PNG\r\n\x1a\n" + b"x" * 1024)
    return p

def test_png_accepted_and_becomes_image_part(png: Path):
    client = FakeClient()
    parts = MultimodalRouter(client).build_input("lihat ini", [png])
    assert parts[0] == {"type": "text", "text": "lihat ini"}
    assert parts[1]["type"] == "image"
    assert parts[1]["uri"].startswith("files/fake-")
    assert parts[1]["mime_type"] == "image/png"

def test_unknown_extension_rejected(tmp_path: Path):
    p = tmp_path / "data.xyz"
    p.write_bytes(b"anything")
    router = MultimodalRouter(FakeClient())
    with pytest.raises(ModalityPolicyError, match="tidak didukung"):
        router.build_input("x", [p])

def test_tool_image_part_is_base64_inline(png: Path):
    part = MultimodalRouter.tool_image_part(png)
    assert part["type"] == "image" and part["mime_type"] == "image/png"
    assert len(part["data"]) > 0           # base64, bukan URI
    assert "uri" not in part
