"""Ingestion pipeline — parser abstraction, dedup, incremental.
Evolusi dari index_builder Vol I: index_ulang() tetap hidup
(backward compat), kini memakai ingest() di bawahnya.
"""
from __future__ import annotations
import hashlib
import re
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

@dataclass(frozen=True)
class DocumentBlock:
    text: str
    heading: str = ""
    page: int | None = None

@dataclass
class ParsedDoc:
    source_path: str
    doc_hash: str
    blocks: list[DocumentBlock] = field(default_factory=list)
    title: str = ""
    mtime: datetime | None = None

class DocParser(ABC):
    """Abstraksi parser — format baru = kelas baru + registrasi."""
    extensions: tuple[str, ...] = ()

    @abstractmethod
    def parse(self, path: Path) -> ParsedDoc: ...

class MarkdownParser(DocParser):
    extensions = (".md", ".markdown", ".txt")

    def parse(self, path: Path) -> ParsedDoc:
        raw = path.read_text(encoding="utf-8", errors="ignore")
        blocks: list[DocumentBlock] = []
        heading = ""
        buffer: list[str] = []

        def flush() -> None:
            if buffer:
                blocks.append(DocumentBlock(text="\n".join(buffer),
                                            heading=heading))
                buffer.clear()

        for line in raw.splitlines():
            m = re.match(r"^(#{1,4})\s+(.*)$", line)
            if m:
                flush()
                heading = m.group(2).strip()
            else:
                buffer.append(line)
        flush()

        return ParsedDoc(source_path=str(path),
                         doc_hash=hashlib.sha256(raw.encode()).hexdigest()[:16],
                         blocks=blocks, title=path.stem,
                         mtime=datetime.fromtimestamp(path.stat().st_mtime,
                                                     tz=timezone.utc))

PARSERS: list[DocParser] = [MarkdownParser()]   # + PdfParser, HtmlParser...

def parser_for(path: Path) -> DocParser:
    for p in PARSERS:
        if path.suffix.lower() in p.extensions:
            return p
    raise ValueError(f"tanpa parser untuk {path.suffix}")

@dataclass(frozen=True)
class Chunk:
    chunk_id: str
    text: str
    source_path: str
    heading: str
    chunk_hash: str
    doc_hash: str

CHUNK_TARGET = 700           # karakter; jendela lembut
CHUNK_OVERLAP = 120

def chunk_quality(text: str) -> float:
    """Skor 0..1 — chunk yang terlalu pendek/panjang atau tanpa
    struktur kalimat menurunkan skor. Dipakai pipeline (bukan
    hanya metrik laporan)."""
    n = len(text)
    if n < 120:
        return 0.2
    size_score = 1.0 if n <= CHUNK_TARGET else max(0.3, CHUNK_TARGET / n)
    sentences = text.count(".") + text.count("\n")
    structure_score = min(1.0, sentences / 6)
    return round(0.6 * size_score + 0.4 * structure_score, 3)

def make_chunks(doc: ParsedDoc) -> list[Chunk]:
    """Potong per blok struktur; kualitas rendah → digabung tetangga."""
    chunks: list[Chunk] = []
    carry = ""

    for i, block in enumerate(doc.blocks):
        heading = block.heading
        text = (carry + "\n" + block.text).strip() if carry else block.text.strip()
        if not text:
            continue
        while len(text) > CHUNK_TARGET + CHUNK_OVERLAP:
            cut = text.rfind(" ", 0, CHUNK_TARGET)
            cut = cut if cut > 200 else CHUNK_TARGET
            piece, text = text[:cut].strip(), text[max(0, cut - CHUNK_OVERLAP):].strip()
            chunks.append(_mk(piece, doc, i, heading))
        if text and chunk_quality(text) < 0.35:
            carry = text                   # terlalu jelek → bawa ke blok berikut
        elif text:
            chunks.append(_mk(text, doc, i, heading))
            carry = ""
    if carry.strip():
        last_heading = doc.blocks[-1].heading if doc.blocks else ""
        chunks.append(_mk(carry.strip(), doc, len(doc.blocks) - 1, last_heading))
    return chunks

def _mk(text: str, doc: ParsedDoc, block_idx: int, heading: str = "") -> Chunk:
    h = hashlib.sha256(text.encode()).hexdigest()[:12]
    return Chunk(chunk_id=f"{doc.doc_hash}-{block_idx}-{h[:6]}",
                 text=text, source_path=doc.source_path,
                 heading=heading, chunk_hash=h,
                 doc_hash=doc.doc_hash)

def ingest(store, docs_dir: Path) -> dict[str, int]:
    """Incremental: hanya dokumen yang hash-nya berubah diproses.
    store: retrieval store Vol I + tabel doc_registry."""
    stats = {"scanned": 0, "updated": 0, "unchanged": 0,
             "chunks_new": 0, "chunks_removed": 0}
    for path in sorted(docs_dir.rglob("*")):
        if not path.is_file():
            continue
        stats["scanned"] += 1
        try:
            doc = parser_for(path).parse(path)
        except ValueError:
            continue                          # format tanpa parser
        known = store.get_doc_hash(doc.source_path)
        if known == doc.doc_hash:
            stats["unchanged"] += 1
            continue
        removed = store.drop_chunks(doc.source_path)   # versi lama hilang
        stats["chunks_removed"] += removed
        for chunk in make_chunks(doc):
            store.upsert_chunk(chunk)        # dedup lewat chunk_hash unik
            stats["chunks_new"] += 1
        store.set_doc_hash(doc.source_path, doc.doc_hash, doc.mtime)
        stats["updated"] += 1
    return stats
