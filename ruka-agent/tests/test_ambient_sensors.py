# -*- coding: utf-8 -*-
"""Tests for Ambient Sensors (Temporal, Geolocation, Weather, Currency)."""
from __future__ import annotations

from typing import Any
import pytest

from src.tools.ambient_sensors import (
    get_current_time,
    get_geolocation,
    get_weather,
    get_currency_rates,
)
from src.gateway.skills.registry import SkillRegistry
from src.gateway.skills.coding_bridge import register_builtin_coding_skills
from src.gateway.skills.runtime import SkillsRuntime
from src.gateway.permissions import PermissionManager
from src.tools.coding import PathJail
from src.ruka_cognition.agentic import make_simple_plan, READ_ONLY_SKILLS


def test_get_current_time_structure() -> None:
    t = get_current_time()
    assert isinstance(t, dict)
    for expected_key in ("day_name", "date", "time", "timezone_name", "iso_timestamp", "greeting_period"):
        assert expected_key in t
    assert len(t["time"].split(":")) >= 2
    assert t["greeting_period"] in ("Pagi", "Siang", "Sore", "Malam")


def test_get_geolocation_fallback() -> None:
    # Function should either return live data or graceful fallback dict
    geo = get_geolocation(timeout=5)
    assert isinstance(geo, dict)
    assert "city" in geo
    assert "latitude" in geo
    assert "longitude" in geo
    assert "country" in geo


def test_get_weather_fallback() -> None:
    w = get_weather(location="Jakarta", timeout=5)
    assert isinstance(w, dict)
    assert "location" in w
    assert "temperature_c" in w
    assert "condition" in w


def test_get_currency_rates_fallback() -> None:
    c = get_currency_rates(base="USD", timeout=5)
    assert isinstance(c, dict)
    assert c.get("base_currency") == "USD"
    assert "rates" in c
    assert "IDR" in c["rates"]


def test_ambient_skills_in_read_only_set() -> None:
    for skill in ("current_time", "geolocation", "weather_info", "currency_rate"):
        assert skill in READ_ONLY_SKILLS


def test_make_simple_plan_ambient_queries() -> None:
    plan_time = make_simple_plan("sekarang jam berapa ya?")
    assert any(s.skill == "current_time" for s in plan_time)

    plan_weather = make_simple_plan("bagaimana cuaca saat ini?")
    assert any(s.skill == "weather_info" for s in plan_weather)

    plan_currency = make_simple_plan("kurs dollar hari ini berapa?")
    assert any(s.skill == "currency_rate" for s in plan_currency)

    plan_geo = make_simple_plan("di mana lokasi saya sekarang?")
    assert any(s.skill == "geolocation" for s in plan_geo)


def test_skills_runtime_executes_current_time(tmp_path: Any) -> None:
    registry = SkillRegistry()
    jail = PathJail(tmp_path)
    register_builtin_coding_skills(registry, jail=jail)
    runtime = SkillsRuntime(registry, PermissionManager(jail))

    res = runtime.execute("current_time", {})
    assert res.success
    assert "day_name" in res.data
    assert "time" in res.data
