import os
from pathlib import Path, PureWindowsPath

class PathLayoutError(Exception):
    pass

APP_DIR_NAME = "Ruka"

DIR_ROLES = ["config", "data", "temp", "cache", "logs", "backups", "ipc", "models"]

ROLE_FLAGS = {
    "config": (False, True, "ditulis jarang; jangan dibaca tiap detik"),
    "data": (False, True, "database memori inti SQLite"),
    "temp": (True, False, "bisa dihapus kapan saja"),
    "cache": (True, False, "data yang bisa direkonstruksi"),
    "logs": (True, False, "JSONL logging"),
    "backups": (False, False, "cadangan snapshot lokal"),
    "ipc": (True, False, "endpoint json sockets"),
    "models": (False, False, "download AI model beban berat"),
}

class WindowsPathLayout:
    """Resolusi + penjara jalur untuk satu instalasi Ruka.
    root disarikan dari %LOCALAPPDATA% (Windows) dengan fallback
    eksplisit untuk pengujian lintas-OS: di Linux, LOCALAPPDATA tak
    ada, jadi pemanggil menyuntikkan root sendiri — perilaku SAMA,
    hanya sumbernya berbeda. Tidak ada satu pun literal C:\\Users.
    """
    def __init__(self, root: str | Path | None = None,
                 *, env: dict[str, str] | None = None):
        if root is None:
            e = dict(os.environ if env is None else env)
            base = e.get("LOCALAPPDATA") or e.get("APPDATA")
            if not base:
                raise PathLayoutError(
                    "LOCALAPPDATA/APPDATA tidak ada di lingkungan — "
                    "suntikkan root= untuk pengujian lintas-OS")
            root = Path(base) / APP_DIR_NAME
        self.root = Path(root)
        self._resolved: dict[str, Path] = {}

    def dir(self, role: str) -> Path:
        """Jalur direktori untuk satu peran; dibuat bila belum ada."""
        if role not in DIR_ROLES:
            raise PathLayoutError(
                f"peran '{role}' tak dikenal; yang sah: {DIR_ROLES}")
        p = self._resolved.get(role)
        if p is None:
            p = self.root / role
            p.mkdir(parents=True, exist_ok=True)
            self._resolved[role] = p
        return p

    def file(self, role: str, name: str) -> Path:
        """Jalur berkas (relative, tanpa subdir) di dalam satu peran."""
        rel = PureWindowsPath(name)
        if rel.is_absolute() or ".." in rel.parts or len(rel.parts) != 1:
            raise PathLayoutError(
                f"nama berkas '{name}' harus satu segmen relatif")
        return self.dir(role) / name

    def confine(self, role: str, rel: str) -> Path:
        """Penjara jalur (keponakan pipeline fileops, lebih ketat):
        resolve() menelan ../ dan symlink, lalu hasil WAJIB
        berprefiks direktori peran. Symlink yang kabur ke luar
        ditolak — bukan karena tidak sopan, tapi karena jail yang
        bisa dikaburkan bukan jail.
        """
        if role not in DIR_ROLES:
            raise PathLayoutError(f"peran '{role}' tak dikenal")
        base = self.dir(role).resolve()
        candidate = (base / rel).resolve()
        try:
            candidate.relative_to(base)
        except ValueError:
            raise PathLayoutError(
                f"jalur '{rel}' kabur dari penjara '{role}' "
                f"(resolve -> {candidate})") from None
        return candidate

    def describe(self) -> dict:
        return {
            "root": str(self.root),
            "roles": {
                r: {
                    "path": str(self.root / r),
                    "regenerable": ROLE_FLAGS[r][0],
                    "backup": ROLE_FLAGS[r][1],
                    "purpose": ROLE_FLAGS[r][2],
                } for r in DIR_ROLES
            },
        }

    def backup_roots(self) -> list[Path]:
        """Peran yang masuk paket backup (lihat backup/manager.py)."""
        return [self.dir(r) for r in DIR_ROLES if ROLE_FLAGS[r][1]]
