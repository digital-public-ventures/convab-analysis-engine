"""Unit tests for token cost calculation helpers."""

from __future__ import annotations

from app.llm import costs


def test_get_model_pricing_for_known_model_profile() -> None:
    pricing = costs.get_model_pricing("gemini-3-flash-preview")
    assert pricing is not None
    assert pricing["input"] == 0.50
    assert pricing["pricing_unit"] == 1_000_000


def test_get_model_pricing_uses_fallback_table_when_profile_missing(monkeypatch) -> None:
    monkeypatch.setattr(costs, "get_model_profile", lambda model_id, models_dict=None: None)
    pricing = costs.get_model_pricing("gpt-5-mini")
    assert pricing is not None
    assert pricing["output"] == 2.00


def test_calculate_cost_returns_rounded_total() -> None:
    total = costs.calculate_cost(
        input_tokens=1000,
        output_tokens=500,
        thinking_tokens=250,
        model_id="gpt-5-mini",
    )
    # (1000*0.25 + 500*2.00 + 250*2.00) / 1_000_000 = 0.00175
    assert total == 0.00175


def test_calculate_cost_unknown_model_returns_zero() -> None:
    assert costs.calculate_cost(100, 100, 100, "unknown-model") == 0.0
