"""Tests for provider-aware model resolution."""

from __future__ import annotations

import pytest

from app.llm.model_config import get_model_profile, validate_model_config
from app.llm.provider import get_llm_provider


def test_model_profile_exposes_provider() -> None:
    profile = get_model_profile("gpt-5.2")
    assert profile is not None
    assert profile.provider == "openai"


def test_provider_filter_rejects_cross_provider_model() -> None:
    profile = get_model_profile("gpt-5.2", provider="gemini")
    assert profile is None


def test_get_llm_provider_infers_from_model_without_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("LLM_PROVIDER", raising=False)
    assert get_llm_provider(model_id_or_key="gpt-5.2") == "openai"


def test_get_llm_provider_rejects_env_conflict(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LLM_PROVIDER", "gemini")
    with pytest.raises(ValueError, match="conflicts with model"):
        get_llm_provider(model_id_or_key="gpt-5.2")


def test_validate_model_config_rejects_provider_mismatch() -> None:
    with pytest.raises(ValueError, match="Invalid model for provider"):
        validate_model_config("gpt-5.2", "MEDIUM", provider="gemini")
