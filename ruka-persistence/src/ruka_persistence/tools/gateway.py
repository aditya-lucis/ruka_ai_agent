import os
import shutil
from pathlib import Path
from ruka_persistence.tools.path_jail import PathJail, detect_binary, ToolError

class IOGateway:
    """Boundary operasi berkas dengan 4 perintah dasar."""
    
    def __init__(self, jail: PathJail):
        self.jail = jail
        self.ignore_dirs = {".git", "node_modules", "__pycache__", ".venv"}
        
    def read_text(self, path: str, max_bytes: int = 512 * 1024) -> str:
        """Membaca teks dari file (maks 512 KiB)."""
        target = self.jail.confine(path)
        if not target.is_file():
            raise ToolError(f"bukan file: {path}")
            
        if detect_binary(target):
            raise ToolError(f"file biner ditolak: {path}")
            
        with target.open("r", encoding="utf-8") as f:
            content = f.read(max_bytes + 1)
            
        if len(content) > max_bytes:
            return content[:max_bytes] + "\n...[TRUNCATED]"
        return content

    def write_text(self, path: str, content: str) -> None:
        """Menulis teks ke file (membuat subdirektori, auto .bak)."""
        target = self.jail.confine(path)
        
        target.parent.mkdir(parents=True, exist_ok=True)
        
        if target.exists():
            bak = target.with_suffix(target.suffix + ".bak")
            shutil.copy2(target, bak)
            
        target.write_text(content, encoding="utf-8")

    def search_text(self, query: str, limit: int = 200) -> list[str]:
        """Mencari file yang mengandung query (kecuali dir abu-abu)."""
        results = []
        
        for root, dirs, files in os.walk(self.jail.base):
            # Prune ignored dirs
            dirs[:] = [d for d in dirs if d not in self.ignore_dirs]
            
            for file in files:
                p = Path(root) / file
                # Skip binary check per file if it's too slow, but here we do it fast
                try:
                    if detect_binary(p):
                        continue
                    
                    text = p.read_text(encoding="utf-8", errors="ignore")
                    if query in text:
                        # Return path relative to base
                        results.append(str(p.relative_to(self.jail.base)).replace("\\", "/"))
                        if len(results) >= limit:
                            results.append(f"...[TRUNCATED AT {limit} HITS]")
                            return results
                except Exception:
                    pass
                    
        return results

    def delete_file(self, path: str, confirmation_token: str) -> bool:
        """Menghapus file tunggal (wajib konfirmasi)."""
        if confirmation_token != "YES_DELETE":
            raise ToolError("token konfirmasi salah")
            
        target = self.jail.confine(path)
        if not target.exists():
            return False
            
        if target.is_dir():
            raise ToolError(f"direktori ditolak: {path}")
            
        target.unlink()
        return True
