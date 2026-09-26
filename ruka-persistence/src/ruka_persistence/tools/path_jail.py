from pathlib import Path

class ToolError(Exception):
    pass

class PathJail:
    """Kurung kerja jalur: resolve + cek prefiks + tolak kabur."""
    def __init__(self, base: str | Path):
        self.base = Path(base).resolve()
        if not self.base.exists():
            raise ToolError(f"base jail tidak ada: {self.base}")
            
    def confine(self, rel: str) -> Path:
        if not rel:
            raise ToolError("jalur kosong")
            
        # Pemisah gaya-Windows dinormalisasi di SEMUA platform.
        # Bug asli tertangkap uji keamanan definitif: di Linux,
        # "..\\..\\x" bukan traversal (backslash bagian NAMA),
        # relative_to lolos — jail tampak aman padahal di Windows
        # string yang sama adalah kabur NYATA.
        # Normalisasi dulu, baru resolve + cek prefiks.
        normalized = rel.replace("\\", "/")
        candidate = (self.base / normalized).resolve()
        
        try:
            candidate.relative_to(self.base)
        except ValueError:
            raise ToolError(
                f"jalur keluar kurung kerja: {rel!r} -> {candidate} "
                f"(base {self.base})") from None
                
        return candidate

def detect_binary(path: Path, peek: int = 8) -> bool:
    with path.open("rb") as f:
        head = f.read(peek)
    
    # Heuristic for NUL-byte
    if b'\x00' in head:
        return True
        
    # Magic bytes for common binaries
    magic = [
        b'\x89PNG\r\n\x1a\n', # PNG
        b'MZ',                # EXE/DLL
        b'\x7fELF',           # ELF
        b'%PDF',              # PDF
        b'PK\x03\x04',        # ZIP
        b'GIF8',              # GIF
        b'\x1f\x8b',          # GZIP
    ]
    for m in magic:
        if head.startswith(m):
            return True
            
    return False
