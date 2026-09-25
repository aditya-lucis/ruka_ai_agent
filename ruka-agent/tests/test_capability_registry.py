from __future__ import annotations
import pytest
from src.capability.registry import (
    CapabilityNotSupported,
    CapabilityRegistry,
    ModelCapability,
    default_registry,
)

def test_default_registry_has_core_models():
    reg = default_registry()
    assert reg.supports("gemini-3.8-flash", "text")
    assert reg.supports("gemini-3.1-flash-live-preview", "live")
    assert reg.supports("gemini-3.1-flash-tts-preview", "audio_output")

def test_gemini_38_flash_is_not_live_model():
    reg = default_registry()
    assert not reg.supports("gemini-3.8-flash", "live")

def test_require_raises_on_unsupported_feature():
    reg = default_registry()
    with pytest.raises(CapabilityNotSupported, match="tidak mendukung"):
        reg.require("gemini-3.8-flash", "live")

def test_require_passes_on_supported_feature():
    reg = default_registry()
    reg.require("gemini-3.1-flash-live-preview", "live")  # no raise

def test_affective_requested_on_31_live_falls_back():
    reg = default_registry()
    extras = reg.live_config_extras("gemini-3.1-flash-live-preview", affective=True)
    assert extras == {}

def test_affective_supported_on_25_live_with_sdk_field():
    reg = CapabilityRegistry(sdk_fields={"enable_affective_dialog"})
    extras = reg.live_config_extras("gemini-2.5-flash-live-preview", affective=True)
    assert extras == {"enable_affective_dialog": True}

def test_affective_fallback_if_sdk_lacks_field():
    reg = CapabilityRegistry(sdk_fields={"other_field"})
    extras = reg.live_config_extras("gemini-2.5-flash-live-preview", affective=True)
    assert extras == {}

def test_unknown_model_defaults_conservative():
    reg = default_registry()
    cap = reg.capability("unknown-future-model")
    assert cap.text is True
    assert cap.image_input is False
    assert cap.live is False

def test_explain_includes_flags():
    reg = default_registry()
    exp = reg.explain("gemini-3.8-flash")
    assert "gemini-3.8-flash" in exp
    assert "function_calling" in exp

def test_default_registry_introspects_real_sdk():
    reg = default_registry()
    # types.LiveConnectConfig in google-genai 2.22+ has model_fields
    assert len(reg._sdk_fields) > 0
