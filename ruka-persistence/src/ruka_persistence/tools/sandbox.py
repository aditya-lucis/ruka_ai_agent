import ast
import builtins
import sys
from ruka_persistence.tools.path_jail import ToolError

class RestrictedSandbox:
    """Sandbox untuk eksekusi Python yang diizinkan (Part XXV)."""
    
    def __init__(self):
        # Allow basic builtins, but reject dangerous ones
        self.allowed_builtins = {
            "print": print,
            "len": len,
            "range": range,
            "str": str,
            "int": int,
            "float": float,
            "bool": bool,
            "list": list,
            "dict": dict,
            "set": set,
            "tuple": tuple,
            "sum": sum,
            "max": max,
            "min": min,
            "abs": abs,
            "round": round,
            "sorted": sorted,
            "isinstance": isinstance,
            "type": type,
            "True": True,
            "False": False,
            "None": None,
        }
        
    def _validate_ast(self, code: str) -> None:
        """Cegah AST node yang berbahaya (misal import)."""
        tree = ast.parse(code)
        for node in ast.walk(tree):
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                raise ToolError("import tidak diizinkan di sandbox")
            if isinstance(node, ast.Call):
                if isinstance(node.func, ast.Name):
                    if node.func.id in ["eval", "exec", "open", "compile", "__import__"]:
                        raise ToolError(f"pemanggilan '{node.func.id}' tidak diizinkan")

    def execute(self, code: str, context_locals: dict = None) -> dict:
        """Eksekusi kode secara terbatas dan kembalikan namespace."""
        self._validate_ast(code)
        
        sandbox_globals = {
            "__builtins__": self.allowed_builtins
        }
        sandbox_locals = context_locals or {}
        
        try:
            exec(code, sandbox_globals, sandbox_locals)
        except Exception as e:
            raise ToolError(f"eksekusi gagal: {e}")
            
        return sandbox_locals
