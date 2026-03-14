"""Tests for model and limiter concurrency caps."""

from app.llm.model_config import MODELS
from app.llm.rate_limiter import AsyncRateLimiter


def test_model_profiles_include_rpm_based_max_concurrency() -> None:
    """Ensure model max_concurrency values match 30% RPM safety margin at 10s/request."""
    assert MODELS["flash"].max_concurrency == 116
    assert MODELS["lite"].max_concurrency == 116
    assert MODELS["pro"].max_concurrency == 2
    assert MODELS["gpt_5_mini"].max_concurrency == 58


def test_tpm_concurrency_limit_respects_upper_bound() -> None:
    """TPM-derived cap should never exceed configured max concurrency."""
    limiter = AsyncRateLimiter(rpm=500, tpm=500_000, rpd=1_000_000, max_concurrency=58)
    assert limiter.calculate_tpm_concurrency_limit(estimated_tokens_per_request=1_000) == 58


def test_tpm_concurrency_limit_scales_down_for_large_batches() -> None:
    """Larger batches should reduce recommended concurrency."""
    limiter = AsyncRateLimiter(rpm=500, tpm=500_000, rpd=1_000_000, max_concurrency=58)
    assert limiter.calculate_tpm_concurrency_limit(estimated_tokens_per_request=10_000) == 5
