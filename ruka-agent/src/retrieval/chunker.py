from __future__ import annotations
import re
from dataclasses import dataclass

@dataclass
class Chunk:
    text: str
    source: str
    heading: str = ""

def chunk_markdown(md: str, source: str, *, target_chars: int = 1200,
                   overlap: int = 200) -> list[Chunk]:
    """Split di batas paragraf dengan overlap — bukan di posisi buta."""
    paras = [p.strip() for p in re.split(r"\n\s*\n", md) if p.strip()]
    chunks: list[Chunk] = []
    buf: list[str] = []
    size = 0
    for p in paras:
        if size + len(p) > target_chars and buf:
            text = "\n\n".join(buf)
            chunks.append(Chunk(text=text, source=source))
            tail = text[-overlap:]  # bawa konteks batas
            buf, size = [tail], len(tail)
        buf.append(p)
        size += len(p)
    if buf:
        chunks.append(Chunk(text="\n\n".join(buf), source=source))
    return chunks
