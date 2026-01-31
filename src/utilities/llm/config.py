"""Configuration for LLM utilities.

This module centralizes configuration values that can be overridden via environment variables.
"""

import os

# Token usage tracking file path
# Default: temp/token_usage.jsonl (relative to working directory)
TOKEN_USAGE_FILE = os.environ.get("TOKEN_USAGE_FILE", "temp/token_usage.jsonl")

# Default schema output directory
SCHEMA_OUTPUT_DIR = os.environ.get("SCHEMA_OUTPUT_DIR", "temp/schemas")
