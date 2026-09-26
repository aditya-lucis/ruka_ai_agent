"""Expression module for Ruka Perception.

Exposes ExpressionState, ExpressionPolicy, HonestyGuard, and STATE_DIMS.
"""

from .state import ExpressionState, STATE_DIMS
from .policy import ExpressionPolicy, HonestyGuard

__all__ = [
    "ExpressionState",
    "STATE_DIMS",
    "ExpressionPolicy",
    "HonestyGuard",
]
