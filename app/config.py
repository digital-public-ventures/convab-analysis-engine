"""Centralized configuration for the app package."""

from pathlib import Path

# Base directory for the app package
BASE_DIR = Path(__file__).parent

# Data directories
DATA_DIR = BASE_DIR / "data"
DOWNLOADS_DIR = DATA_DIR / "downloads"
CLEANED_DATA_DIR = DATA_DIR / "cleaned_data"
RAW_DATA_DIR = DATA_DIR / "raw"

# Supported file extensions for attachments
ATTACHMENT_EXTENSIONS = frozenset({".pdf", ".jpg", ".jpeg", ".png", ".docx"})
IMAGE_EXTENSIONS = frozenset({".png", ".jpg", ".jpeg", ".tif", ".tiff"})
DOCUMENT_EXTENSIONS = frozenset({".pdf", ".docx"})

# HTTP settings
DEFAULT_TIMEOUT = 30.0
MAX_DOWNLOAD_CONCURRENCY = 200

# Schema generation settings
SCHEMA_DEFAULT_SAMPLE_SIZE = 10
SCHEMA_DEFAULT_HEAD_SIZE = 5
SCHEMA_MODEL_ID = "gemini-3-flash-preview"
SCHEMA_THINKING_LEVEL = "MINIMAL"

# Token usage tracking
TOKEN_USAGE_FILE = DATA_DIR / "token_usage.jsonl"

# Logging format
LOG_FORMAT = "%(asctime)s.%(msecs)03d [%(levelname)s] %(message)s"
LOG_DATE_FORMAT = "%H:%M:%S"
