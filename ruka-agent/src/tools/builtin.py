from __future__ import annotations
import ast
import operator
from datetime import datetime
from typing import ClassVar
from pydantic import BaseModel, Field
from src.tools.base import BaseTool, ToolError

class CalcArgs(BaseModel):
    expression: str = Field(
        description="Aritmetika: angka, + - * / ( )."
    )

class CalculatorTool(BaseTool):
    name: str = "calculator"
    description: str = (
        "Hitung ekspresi aritmetika dengan presisi tinggi. "
        "Gunakan untuk SEMUA perhitungan angka."
    )
    args_model: type[BaseModel] = CalcArgs
    timeout_s: float = 2.0
    
    OPS: ClassVar[dict] = {
        ast.Add: operator.add, ast.Sub: operator.sub,
        ast.Mult: operator.mul, ast.Div: operator.truediv,
        ast.USub: operator.neg,
    }
    
    def run(self, args: CalcArgs) -> float:
        """Parse AST yang aman — bukan eval() mentah."""
        tree = ast.parse(args.expression, mode="eval")
        return self._eval(tree.body)
        
    def _eval(self, node) -> float:
        if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
            return node.value
        if isinstance(node, ast.BinOp) and type(node.op) in self.OPS:
            return self.OPS[type(node.op)](self._eval(node.left),
                                           self._eval(node.right))
        if isinstance(node, ast.UnaryOp) and type(node.op) in self.OPS:
            return self.OPS[type(node.op)](self._eval(node.operand))
        raise ToolError("ekspresi tidak didukung")

class DateTimeArgs(BaseModel):
    tz: str = Field(default="Asia/Jakarta", description="Zona waktu.")

class DateTimeTool(BaseTool):
    name: str = "current_datetime"
    description: str = "Waktu sekarang dalam zona waktu tertentu."
    args_model: type[BaseModel] = DateTimeArgs
    
    def run(self, args: DateTimeArgs) -> str:
        from zoneinfo import ZoneInfo
        now = datetime.now(ZoneInfo(args.tz))
        return now.isoformat(timespec="seconds")
