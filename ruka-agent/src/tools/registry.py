from __future__ import annotations
import concurrent.futures
from src.tools.base import BaseTool, ToolError

class ToolRegistry:
    def __init__(self):
        self._tools: dict[str, BaseTool] = {}
        
    def register(self, tool: BaseTool) -> None:
        if tool.name in self._tools:
            raise ValueError(f"tool duplikat: {tool.name}")
        self._tools[tool.name] = tool
        
    def declarations(self) -> list[dict]:
        """Bentuk 'type: function' untuk tools= parameter API."""
        return [
            {
                "type": "function",
                "name": t.name,
                "description": t.description,
                "parameters": t.args_model.model_json_schema(),
            }
            for t in self._tools.values()
        ]
        
    def execute(self, name: str, raw_args: dict,
                *, granted: set[str]) -> dict:
        """Eksekusi + timeout. Selalu balik dict (kontrak loop)."""
        tool = self._tools.get(name)
        if tool is None:
            return {"error": f"tool tidak dikenal: {name}"}
        
        try:
            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as ex:
                fut = ex.submit(tool.execute, raw_args, granted=granted)
                return {"result": fut.result(timeout=tool.timeout_s)}
        except concurrent.futures.TimeoutError:
            return {"error": f"{name}: timeout {tool.timeout_s}s"}
        except ToolError as e:
            return {"error": str(e)}
