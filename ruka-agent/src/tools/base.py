from __future__ import annotations
import logging
import time
from abc import ABC, abstractmethod
from typing import Any
from pydantic import BaseModel

log = logging.getLogger("ruka.tools")

class ToolError(Exception):
    """Error terstruktur: masuk history, bukan crash loop."""

class BaseTool(ABC, BaseModel):
    name: str
    description: str            # dikirim ke model sebagai petunjuk
    args_model: type[BaseModel]
    timeout_s: float = 10.0
    requires_permission: bool = False
    
    @abstractmethod
    def run(self, args: BaseModel) -> Any:
        """Eksekusi inti — harus idempotent bila memungkinkan."""
    
    def execute(self, raw_args: dict, *, granted: set[str]) -> Any:
        """Gerbang kontrak: validasi -> izin -> timeout -> log."""
        if self.requires_permission and self.name not in granted:
            raise ToolError(f"tool '{self.name}' butuh izin")
        
        args = self.args_model.model_validate(raw_args)
        t0 = time.monotonic()
        try:
            result = self.run(args)
            log.info("tool=%s durasi=%.2fs ok", self.name,
                     time.monotonic() - t0)
            return result
        except ToolError:
            raise
        except Exception as e:
            log.exception("tool=%s gagal", self.name)
            raise ToolError(f"{self.name}: {e}") from e
