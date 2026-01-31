"""Async rate limiter for API calls with RPM, TPM, and RPD limits."""

import asyncio
import logging
import time

from google import genai

logger = logging.getLogger(__name__)


class RateLimitExceededError(Exception):
    """Raised when API rate limits are exceeded and cannot be waited out."""


class AsyncRateLimiter:
    """Async rate limiter using sliding window for minute limits and counter for daily limits.

    This class manages three types of rate limits:
    - RPM (Requests Per Minute): Maximum number of requests in a 60-second window
    - TPM (Tokens Per Minute): Maximum number of tokens in a 60-second window
    - RPD (Requests Per Day): Maximum number of requests in a 24-hour period

    The sliding window approach for RPM/TPM allows for smooth request distribution
    rather than hard resets at minute boundaries.
    """

    def __init__(self, rpm: int, tpm: int, rpd: int, max_concurrency: int = 60):
        """Initialize the rate limiter.

        Args:
            rpm: Maximum requests per minute
            tpm: Maximum tokens per minute
            rpd: Maximum requests per day
            max_concurrency: Maximum concurrent requests (default: 60)
        """
        self.rpm_limit = rpm
        self.tpm_limit = tpm
        self.rpd_limit = rpd
        self._semaphore = asyncio.Semaphore(max_concurrency)

        self.request_timestamps: list[float] = []
        self.token_timestamps: list[tuple[float, int]] = []
        self.daily_request_count = 0
        self.day_start = time.time()
        self._lock = asyncio.Lock()

    async def acquire(self, estimated_tokens: int) -> None:
        """Acquire a rate limit slot, waiting if necessary.

        This method implements a sliding window algorithm:
        1. Checks if daily limit is exceeded (raises if so)
        2. Prunes timestamps older than 60 seconds
        3. Waits if RPM limit would be exceeded
        4. Waits if TPM limit would be exceeded
        5. Records the request timestamp and token count

        Args:
            estimated_tokens: Estimated total tokens for this request

        Raises:
            RateLimitExceededError: If daily request limit is exceeded
        """
        async with self._lock:
            now = time.time()

            # 1. Reset daily limit if 24h passed
            if now - self.day_start > 86400:
                self.daily_request_count = 0
                self.day_start = now

            if self.daily_request_count >= self.rpd_limit:
                raise RateLimitExceededError(f"Daily request limit ({self.rpd_limit}) exceeded")

            # 2. Prune old timestamps (older than 60s)
            self.request_timestamps = [t for t in self.request_timestamps if now - t < 60]
            self.token_timestamps = [(t, c) for t, c in self.token_timestamps if now - t < 60]

            # 3. Check RPM
            while len(self.request_timestamps) >= self.rpm_limit:
                wait_time = 60 - (now - self.request_timestamps[0]) + 0.1
                logger.info(f"RPM limit reached, waiting {wait_time:.2f}s")
                await asyncio.sleep(wait_time)
                now = time.time()
                # Re-prune after waiting
                self.request_timestamps = [t for t in self.request_timestamps if now - t < 60]

            # 4. Check TPM
            current_tpm = sum(c for _, c in self.token_timestamps)
            while current_tpm + estimated_tokens > self.tpm_limit:
                # Find how long until enough tokens expire
                needed_to_free = (current_tpm + estimated_tokens) - self.tpm_limit
                freed = 0
                wait_until = now

                for t, c in self.token_timestamps:
                    freed += c
                    if freed >= needed_to_free:
                        wait_until = t + 60.1
                        break

                wait_time = max(0.1, wait_until - time.time())
                logger.info(f"TPM limit reached, waiting {wait_time:.2f}s")
                await asyncio.sleep(wait_time)
                now = time.time()
                # Re-prune and re-calc
                self.token_timestamps = [(t, c) for t, c in self.token_timestamps if now - t < 60]
                current_tpm = sum(c for _, c in self.token_timestamps)

            # 5. Record usage
            self.request_timestamps.append(now)
            self.token_timestamps.append((now, estimated_tokens))
            self.daily_request_count += 1

    async def acquire_concurrency(self) -> None:
        """Acquire a concurrency slot from the semaphore.

        Call this before starting a request to limit concurrent API calls.
        Must be paired with release_concurrency() when the request completes.
        """
        await self._semaphore.acquire()

    def release_concurrency(self) -> None:
        """Release a concurrency slot back to the semaphore.

        Call this when a request completes (in a finally block) to allow
        other requests to proceed.
        """
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

        This is a convenience method that combines token counting with rate limit
        acquisition. It uses the Gemini API to count input tokens accurately,
        then estimates output tokens based on the provided parameters.

        Args:
            client: Gemini API client instance
            model_id: Full model ID (e.g., 'gemini-3-flash-preview')
            prompt_text: The prompt text to count tokens for
            system_instruction: Optional system instruction (counted in tokens)
            estimated_output_tokens_per_item: Estimated output tokens per item (default: 500)
            batch_size: Number of items in the batch (default: 1)

        Returns:
            Actual input token count (not the estimated total)

        Raises:
            RateLimitExceededError: If daily request limit is exceeded
        """
        # Build content string for token counting
        content = system_instruction + prompt_text if system_instruction else prompt_text

        # Count input tokens using API
        token_resp = await client.aio.models.count_tokens(model=model_id, contents=content)
        estimated_input_tokens = int(token_resp.total_tokens or 0)

        # Estimate total tokens (conservative estimate for output)
        estimated_total_tokens = estimated_input_tokens + (estimated_output_tokens_per_item * batch_size)

        # Acquire rate limit slot
        await self.acquire(estimated_total_tokens)

        return estimated_input_tokens
