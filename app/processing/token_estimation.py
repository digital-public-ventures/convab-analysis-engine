"""Shared token estimation helpers for sampled record payloads."""

from __future__ import annotations

import json
import math
import re
import string
from typing import Any


def estimate_tokens(value: Any) -> int:
    """Estimate tokens using the same heuristic as AsyncRateLimiter."""
    content = json.dumps(value, default=str)
    split_pattern = rf"[{re.escape(string.punctuation)}\s]+"
    words = [word for word in re.split(split_pattern, content) if word]
    return max(1, math.ceil(len(words) / 0.75))
