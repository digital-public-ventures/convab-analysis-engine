"""Async rate limiter for API calls with RPM, TPM, and RPD limits."""

import asyncio
import logging
import math
import re
import string
import time

from google import genai

logger = logging.getLogger(__name__)


class RateLimitExceededError(Exception):
    """Raised when API rate limits are exceeded."""


class AsyncRateLimiter:
    """Tracks RPM, TPM, and RPD using a sliding window approach for minute limits
    and a simple counter for daily limits.
    """

    def __init__(self, rpm: int, tpm: int, rpd: int, max_concurrency: int = 60):
        """Initialize the rate limiter.

        Args:
            rpm: Requests per minute limit
            tpm: Tokens per minute limit
            rpd: Requests per day limit
            max_concurrency: Maximum concurrent requests (default: 60)
        """
        self.rpm_limit = rpm
        self.tpm_limit = tpm
        self.rpd_limit = rpd
        self.max_concurrency_limit = max(1, max_concurrency)
        self._semaphore = asyncio.Semaphore(self.max_concurrency_limit)

        self.request_timestamps: list[float] = []
        self.token_timestamps: list[tuple[float, int]] = []
        self.daily_request_count = 0
        self.day_start = time.time()
        self._lock = asyncio.Lock()

    def calculate_tpm_concurrency_limit(
        self,
        estimated_tokens_per_request: int,
        safety_margin: float = 0.30,
        expected_request_seconds: float = 10.0,
    ) -> int:
        """Estimate a safe concurrency cap from TPM for a request shape.

        This does not change the active semaphore size yet; it is a planning
        helper for callers to choose a task fan-out bounded by model config.
        """
        if estimated_tokens_per_request <= 0:
            return self.max_concurrency_limit

        safe_tpm_budget = max(1, math.floor(self.tpm_limit * (1 - safety_margin)))
        requests_per_worker_per_minute = max(1.0, 60.0 / max(expected_request_seconds, 0.1))
        tokens_per_worker_per_minute = max(
            1,
            math.ceil(estimated_tokens_per_request * requests_per_worker_per_minute),
        )
        tpm_cap = max(1, safe_tpm_budget // tokens_per_worker_per_minute)
        return min(self.max_concurrency_limit, tpm_cap)

    async def acquire(self, estimated_tokens: int) -> None:
        """Acquire a rate limit slot, waiting if necessary.

        Args:
            estimated_tokens: Estimated total tokens for the request

        Raises:
            RateLimitExceededError: If daily request limit is exceeded
        """
        async with self._lock:
            now = time.time()

            # Reset daily limit if 24h passed
            if now - self.day_start > 86400:
                self.daily_request_count = 0
                self.day_start = now

            if self.daily_request_count >= self.rpd_limit:
                raise RateLimitExceededError(f'Daily request limit ({self.rpd_limit}) exceeded.')

            # Prune old timestamps (older than 60s)
            self.request_timestamps = [t for t in self.request_timestamps if now - t < 60]
            self.token_timestamps = [(t, c) for t, c in self.token_timestamps if now - t < 60]

            # Check RPM
            while len(self.request_timestamps) >= self.rpm_limit:
                wait_time = 60 - (now - self.request_timestamps[0]) + 0.1
                logger.debug('RPM cap hit. Waiting %.2fs...', wait_time)
                await asyncio.sleep(wait_time)
                now = time.time()
                self.request_timestamps = [t for t in self.request_timestamps if now - t < 60]

            # Check TPM
            current_tpm = sum(c for _, c in self.token_timestamps)
            while current_tpm + estimated_tokens > self.tpm_limit:
                needed_to_free = (current_tpm + estimated_tokens) - self.tpm_limit
                freed = 0
                wait_until = now

                for t, c in self.token_timestamps:
                    freed += c
                    if freed >= needed_to_free:
                        wait_until = t + 60.1
                        break

                wait_time = max(0.1, wait_until - time.time())
                logger.debug('TPM cap hit. Waiting %.2fs...', wait_time)
                await asyncio.sleep(wait_time)
                now = time.time()
                self.token_timestamps = [(t, c) for t, c in self.token_timestamps if now - t < 60]
                current_tpm = sum(c for _, c in self.token_timestamps)

            # Record usage
            self.request_timestamps.append(now)
            self.token_timestamps.append((now, estimated_tokens))
            self.daily_request_count += 1

    async def acquire_concurrency(self) -> None:
        """Acquire a concurrency slot."""
        await self._semaphore.acquire()

    def release_concurrency(self) -> None:
        """Release a concurrency slot."""
        self._semaphore.release()

    async def count_tokens_and_acquire(
        self,
        client: genai.Client,
        model_id: str,
        prompt_text: str,
        system_instruction: str | None = None,
        estimated_output_tokens_per_item: int = 500,
        batch_size: int = 1,
    ) -> int:
        """Count input tokens and estimate total, then acquire rate limit slot.

        Args:
            client: Gemini API client instance
            model_id: Full model ID (e.g., 'gemini-3-flash-preview')
            prompt_text: The prompt text to count tokens for
            system_instruction: Optional system instruction (counted in tokens)
            estimated_output_tokens_per_item: Estimated output tokens per item (default: 500)
            batch_size: Number of items in the batch (default: 1)

        Returns:
            Estimated total tokens (input + estimated output)
        """
        content = system_instruction + prompt_text if system_instruction else prompt_text
        split_pattern = rf'[{re.escape(string.punctuation)}\s]+'
        words = [word for word in re.split(split_pattern, content) if word]
        estimated_input_tokens = max(1, math.ceil(len(words) / 0.75))

        estimated_total_tokens = estimated_input_tokens + (estimated_output_tokens_per_item * batch_size)
        recommended_concurrency = self.calculate_tpm_concurrency_limit(estimated_total_tokens)
        if recommended_concurrency < self.max_concurrency_limit:
            logger.debug(
                (
                    'TPM-based concurrency recommendation for this request shape: %d '
                    '(upper_limit=%d, estimated_total_tokens=%d)'
                ),
                recommended_concurrency,
                self.max_concurrency_limit,
                estimated_total_tokens,
            )

        await self.acquire(estimated_total_tokens)

        return estimated_input_tokens
