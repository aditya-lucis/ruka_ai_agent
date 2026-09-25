# -*- coding: utf-8 -*-
"""Fixture bersama: FakeClient kontrak Interactions API v2.
Meniru BENTUK permukaan yang dipakai ruka-agent:
- interactions.create(model, input, tools, system_instruction,
  response_format, store) -> Interaction(output_text, steps, usage)
- step keluaran: type function_call (name, arguments, id) | text
Kontrak ini dijaga test_contracts saat SDK naik versi.
"""
from __future__ import annotations
import json
from dataclasses import dataclass, field
import pytest


@dataclass
class FakeStep:
    type: str                          # "function_call" | "text"
    name: str | None = None
    arguments: dict | None = None
    id: str | None = None
    text: str | None = None

    def model_dump(self) -> dict:
        return {
            "type": self.type,
            "name": self.name,
            "arguments": self.arguments,
            "id": self.id,
            "text": self.text,
        }


@dataclass
class FakeInteraction:
    output_text: str = ""
    steps: list = field(default_factory=list)
    usage: dict = field(default_factory=lambda: {"tokens": 0})


class FakeInteractions:
    """Skrip per panggilan: daftar respon yang dikonsumsi berurutan."""
    def __init__(self, responses: list[FakeInteraction]) -> None:
        self._responses = list(responses)
        self.calls: list[dict] = []

    def create(self, **kwargs) -> FakeInteraction:
        self.calls.append(kwargs)
        if not self._responses:
            return FakeInteraction(output_text="(habis skrip)")
        return self._responses.pop(0)


class FakeClient:
    def __init__(self, responses: list[FakeInteraction]) -> None:
        self.interactions = FakeInteractions(responses)


@pytest.fixture()
def fake_client():
    return lambda responses: FakeClient(responses)
