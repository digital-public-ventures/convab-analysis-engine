"""Slow integration test for rate-limiter throughput on a large fixture."""

from __future__ import annotations

import asyncio
import csv
import logging
import math
import re
import string
import time
from pathlib import Path

import pytest

from app.llm.model_config import MODELS, RPM_SAFETY_MARGIN
from app.llm.rate_limiter import AsyncRateLimiter

FIXTURES_DIR = Path(__file__).parent / "fixtures"
RAW_5000_CSV = FIXTURES_DIR / "raw" / "clean_5000.csv"
DEVELOPMENT_LOG_PATH = Path("temp/notes/rate_limiter_throughput.log")


def _estimate_input_tokens(content: str) -> int:
    """Mirror AsyncRateLimiter token estimation."""
    split_pattern = rf"[{re.escape(string.punctuation)}\s]+"
    words = [word for word in re.split(split_pattern, content) if word]
    return max(1, math.ceil(len(words) / 0.75))


def _load_prompts_for_batches(csv_path: Path, batch_size: int = 5, max_rows: int = 5000) -> list[str]:
    """Build batched prompt text from the 5k fixture."""
    csv.field_size_limit(10**9)
    rows: list[tuple[str, str]] = []
    with csv_path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        for idx, row in enumerate(reader):
            if idx >= max_rows:
                break
            rows.append((str(row.get("Document ID", "")), str(row.get("Comment", ""))))

    prompts: list[str] = []
    for offset in range(0, len(rows), batch_size):
        chunk = rows[offset : offset + batch_size]
        lines = [f"record_id={record_id}\ncomment={comment}" for record_id, comment in chunk]
        prompts.append("\n\n".join(lines))
    return prompts


async def _mock_llm_call() -> dict[str, object]:
    """Mock LLM call latency and success response."""
    await asyncio.sleep(5.0)
    return {"ok": True}


def _build_worker_count_and_limits(
    profile_rpm: int,
    profile_tpm: int,
    profile_max_concurrency: int,
    avg_tokens_per_request: int,
) -> tuple[int, int, int]:
    """Calculate safe RPM/TPM thresholds and worker count."""
    safe_rpm = math.floor(profile_rpm * (1 - RPM_SAFETY_MARGIN))
    safe_tpm = math.floor(profile_tpm * (1 - RPM_SAFETY_MARGIN))
    requests_per_worker_per_minute = 12  # 5s mocked latency
    rpm_based_workers = max(1, safe_rpm // requests_per_worker_per_minute)
    limiter_for_calc = AsyncRateLimiter(
        rpm=profile_rpm,
        tpm=profile_tpm,
        rpd=1_000_000,
        max_concurrency=profile_max_concurrency,
    )
    tpm_based_workers = limiter_for_calc.calculate_tpm_concurrency_limit(
        estimated_tokens_per_request=avg_tokens_per_request,
        safety_margin=RPM_SAFETY_MARGIN,
        expected_request_seconds=5.0,
    )
    worker_count = max(1, min(profile_max_concurrency, rpm_based_workers, tpm_based_workers))
    return worker_count, safe_rpm, safe_tpm


def _configure_file_logger() -> tuple[logging.Logger, logging.FileHandler]:
    """Create a deterministic file logger for development review."""
    DEVELOPMENT_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    logger = logging.getLogger("rate_limiter_throughput_integration")
    logger.setLevel(logging.INFO)
    logger.handlers = []
    file_handler = logging.FileHandler(DEVELOPMENT_LOG_PATH, mode="a", encoding="utf-8")
    file_handler.setFormatter(logging.Formatter("%(asctime)s %(message)s"))
    logger.addHandler(file_handler)
    return logger, file_handler


async def _run_60s_throughput_measurement(
    limiter: AsyncRateLimiter,
    prompts: list[str],
    profile_model_id: str,
    worker_count: int,
    logger: logging.Logger,
) -> tuple[int, int]:
    """Run workers for a 60s window and return (requests, tokens)."""
    stats: dict[str, float] = {"requests": 0.0, "tokens": 0.0, "first_sent_at": 0.0}
    stats_lock = asyncio.Lock()
    start_event = asyncio.Event()
    stop_event = asyncio.Event()
    total_prompts = len(prompts)
    prompt_index = 0
    prompt_index_lock = asyncio.Lock()

    async def get_next_prompt() -> str:
        nonlocal prompt_index
        async with prompt_index_lock:
            prompt = prompts[prompt_index % total_prompts]
            prompt_index += 1
            return prompt

    async def worker(worker_id: int) -> None:
        while not stop_event.is_set():
            prompt = await get_next_prompt()
            await limiter.acquire_concurrency()
            try:
                estimated_input_tokens = await limiter.count_tokens_and_acquire(
                    client=object(),  # Not used by count_tokens_and_acquire.
                    model_id=profile_model_id,
                    prompt_text=prompt,
                    system_instruction=None,
                    estimated_output_tokens_per_item=500,
                    batch_size=5,
                )
                estimated_total_tokens = estimated_input_tokens + (500 * 5)
                async with stats_lock:
                    sent_at = time.monotonic()
                    if stats["first_sent_at"] == 0.0:
                        stats["first_sent_at"] = sent_at
                        start_event.set()
                    if sent_at - stats["first_sent_at"] <= 60.0:
                        stats["requests"] += 1.0
                        stats["tokens"] += float(estimated_total_tokens)
                    else:
                        stop_event.set()
                        break
                _ = await _mock_llm_call()
            finally:
                limiter.release_concurrency()

            if worker_id == 0 and int(stats["requests"]) % 10 == 0:
                logger.info("progress requests=%d tokens=%d", int(stats["requests"]), int(stats["tokens"]))

    workers = [asyncio.create_task(worker(idx)) for idx in range(worker_count)]
    await asyncio.wait_for(start_event.wait(), timeout=30.0)
    await asyncio.sleep(60.0)
    stop_event.set()
    await asyncio.gather(*workers, return_exceptions=True)
    return int(stats["requests"]), int(stats["tokens"])


@pytest.mark.asyncio
@pytest.mark.slow
@pytest.mark.integration
async def test_rate_limiter_5k_fixture_throughput_with_safety_margin() -> None:
    """Measure 60s throughput and assert it stays within 30% safety margin."""
    profile = MODELS["gpt_5_mini"]
    limiter = AsyncRateLimiter(
        rpm=profile.rpm,
        tpm=profile.tpm,
        rpd=profile.rpd,
        max_concurrency=profile.max_concurrency,
    )
    prompts = _load_prompts_for_batches(RAW_5000_CSV, batch_size=5, max_rows=5000)
    assert prompts, "Expected non-empty prompts from clean_5000.csv"

    sample_tokens = [_estimate_input_tokens(prompt) + (500 * 5) for prompt in prompts[:100]]
    avg_tokens_per_request = max(1, math.ceil(sum(sample_tokens) / len(sample_tokens)))

    worker_count, safe_rpm, safe_tpm = _build_worker_count_and_limits(
        profile_rpm=profile.rpm,
        profile_tpm=profile.tpm,
        profile_max_concurrency=profile.max_concurrency,
        avg_tokens_per_request=avg_tokens_per_request,
    )
    logger, file_handler = _configure_file_logger()
    measured_requests, measured_tokens = await _run_60s_throughput_measurement(
        limiter=limiter,
        prompts=prompts,
        profile_model_id=profile.model_id,
        worker_count=worker_count,
        logger=logger,
    )
    measured_rpm = measured_requests  # 60-second measurement window
    measured_tpm = measured_tokens  # 60-second measurement window

    logger.info(
        (
            "summary workers=%d requests=%d tokens=%d measured_rpm=%d measured_tpm=%d "
            "safe_rpm=%d safe_tpm=%d avg_tokens_per_request=%d"
        ),
        worker_count,
        measured_requests,
        measured_tokens,
        measured_rpm,
        measured_tpm,
        safe_rpm,
        safe_tpm,
        avg_tokens_per_request,
    )
    file_handler.flush()
    logger.removeHandler(file_handler)
    file_handler.close()

    assert measured_rpm <= safe_rpm
    assert measured_tpm <= safe_tpm
