"""Async rate limiter for API calls with RPM, TPM, and RPD limits."""

import asyncio
import time

from google import genai


class AsyncRateLimiter:
    """Tracks RPM, TPM, and RPD using a sliding window approach for minute limits
    and a simple counter for daily limits.
    """

    def __init__(self, rpm: int, tpm: int, rpd: int):
        self.rpm_limit = rpm
        self.tpm_limit = tpm
        self.rpd_limit = rpd

        self.request_timestamps = []  # List of floats (timestamps)
        self.token_timestamps = []  # List of tuples (timestamp, token_count)
        self.daily_request_count = 0
        self.day_start = time.time()
        self._lock = asyncio.Lock()

    async def acquire(self, estimated_tokens: int):
        async with self._lock:
            now = time.time()

            # 1. Reset Daily Limit if 24h passed
            if now - self.day_start > 86400:
                self.daily_request_count = 0
                self.day_start = now

            if self.daily_request_count >= self.rpd_limit:
                raise Exception(f'Daily Request Limit ({self.rpd_limit}) Exceeded.')

            # 2. Prune old timestamps (older than 60s)
            self.request_timestamps = [t for t in self.request_timestamps if now - t < 60]
            self.token_timestamps = [(t, c) for t, c in self.token_timestamps if now - t < 60]

            # 3. Check RPM
            while len(self.request_timestamps) >= self.rpm_limit:
                wait_time = 60 - (now - self.request_timestamps[0]) + 0.1
                print(f'  [Rate Limit] RPM cap hit. Waiting {wait_time:.2f}s...')
                await asyncio.sleep(wait_time)
                now = time.time()
                # Re-prune after waiting
                self.request_timestamps = [t for t in self.request_timestamps if now - t < 60]

            # 4. Check TPM
            current_tpm = sum(c for _, c in self.token_timestamps)
            while current_tpm + estimated_tokens > self.tpm_limit:
                # Find how long until enough tokens expire
                # We need to free up: (current + new - limit)
                needed_to_free = (current_tpm + estimated_tokens) - self.tpm_limit
                freed = 0
                wait_until = now

                for t, c in self.token_timestamps:
                    freed += c
                    if freed >= needed_to_free:
                        wait_until = t + 60.1
                        break

                wait_time = max(0.1, wait_until - time.time())
                print(f'  [Rate Limit] TPM cap hit. Waiting {wait_time:.2f}s...')
                await asyncio.sleep(wait_time)
                now = time.time()
                # Re-prune and re-calc
                self.token_timestamps = [(t, c) for t, c in self.token_timestamps if now - t < 60]
                current_tpm = sum(c for _, c in self.token_timestamps)

            # 5. Record usage
            self.request_timestamps.append(now)
            self.token_timestamps.append((now, estimated_tokens))
            self.daily_request_count += 1

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
        # Build content string for token counting
        content = system_instruction + prompt_text if system_instruction else prompt_text

        # Count input tokens using API
        token_resp = await client.aio.models.count_tokens(model=model_id, contents=content)
        estimated_input_tokens = token_resp.total_tokens

        # Estimate total tokens (conservative estimate for output)
        estimated_total_tokens = estimated_input_tokens + (estimated_output_tokens_per_item * batch_size)

        # Acquire rate limit slot
        await self.acquire(estimated_total_tokens)

        return estimated_input_tokens
