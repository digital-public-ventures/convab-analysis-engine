"""Unit tests for LLM utility helpers."""

from __future__ import annotations

import pytest

from app.llm import costs
from app.llm.model_config import get_model_profile, validate_model_config
from app.llm.provider import get_llm_provider
from app.llm.response_parser import extract_json_from_response


def test_get_model_pricing_for_known_model_profile() -> None:
    pricing = costs.get_model_pricing('gemini-3-flash-preview')
    assert pricing is not None
    assert pricing['input'] == 0.50
    assert pricing['pricing_unit'] == 1_000_000


def test_get_model_pricing_uses_fallback_table_when_profile_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(costs, 'get_model_profile', lambda model_id, models_dict=None: None)
    pricing = costs.get_model_pricing('gpt-5-mini')
    assert pricing is not None
    assert pricing['output'] == 2.00


def test_calculate_cost_returns_rounded_total() -> None:
    total = costs.calculate_cost(
        input_tokens=1000,
        output_tokens=500,
        thinking_tokens=250,
        model_id='gpt-5-mini',
    )
    # (1000*0.25 + 500*2.00 + 250*2.00) / 1_000_000 = 0.00175
    assert total == 0.00175


def test_calculate_cost_unknown_model_returns_zero() -> None:
    assert costs.calculate_cost(100, 100, 100, 'unknown-model') == 0.0


def test_extract_json_from_response_passthrough_dict() -> None:
    payload = {'records': [{'record_id': '1'}]}
    assert extract_json_from_response(payload) == payload


def test_extract_json_from_response_from_markdown_block() -> None:
    wrapped = {'text': '```json\n{"records":[{"record_id":"1"}]}\n```'}
    parsed = extract_json_from_response(wrapped)
    assert parsed['records'][0]['record_id'] == '1'


def test_extract_json_from_response_from_raw_string() -> None:
    raw = '{"records":[{"record_id":"abc"}]}'
    parsed = extract_json_from_response(raw)
    assert parsed['records'][0]['record_id'] == 'abc'


def test_extract_json_from_response_rejects_invalid_type() -> None:
    with pytest.raises(ValueError, match='Unsupported response type'):
        extract_json_from_response(123)  # type: ignore[arg-type]


def test_extract_json_from_response_invalid_json_includes_preview() -> None:
    with pytest.raises(ValueError, match='Failed to parse JSON response'):
        extract_json_from_response({'text': '```json\n{not valid json}\n```'})


def test_model_profile_exposes_provider() -> None:
    profile = get_model_profile('gpt-5.2')
    assert profile is not None
    assert profile.provider == 'openai'


def test_provider_filter_rejects_cross_provider_model() -> None:
    profile = get_model_profile('gpt-5.2', provider='gemini')
    assert profile is None


def test_get_llm_provider_infers_from_model_without_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv('LLM_PROVIDER', raising=False)
    assert get_llm_provider(model_id_or_key='gpt-5.2') == 'openai'


def test_get_llm_provider_rejects_env_conflict(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv('LLM_PROVIDER', 'gemini')
    with pytest.raises(ValueError, match='conflicts with model'):
        get_llm_provider(model_id_or_key='gpt-5.2')


def test_validate_model_config_rejects_provider_mismatch() -> None:
    with pytest.raises(ValueError, match='Invalid model for provider'):
        validate_model_config('gpt-5.2', 'MEDIUM', provider='gemini')
