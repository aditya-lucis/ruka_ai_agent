# -*- coding: utf-8 -*-
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Mapping, Any

def check_kind(kind: str) -> None:
    if not kind:
        raise ValueError("kind cannot be empty")

@dataclass(frozen=True)
class Document:
    doc_id: str
    text: str
    kind: str
    metadata: Mapping[str, Any] = field(default_factory=dict)

@dataclass(frozen=True)
class ScoredMatch:
    document: Document
    similarity: float
    score: float
