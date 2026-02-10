"""Centralized configuration for the app package."""

import os
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
UNSUPPORTED_ATTACHMENT_EXTENSIONS = frozenset(
    f'.{ext.strip().lstrip(".")}'
    for ext in os.environ.get("UNSUPPORTED_ATTACHMENT_EXTENSIONS", "").split(",")
    if ext.strip()
)

# HTTP settings
DEFAULT_TIMEOUT = 30.0
MAX_DOWNLOAD_CONCURRENCY = 200

# Cleaning settings
CLEAN_CHUNK_SIZE = 50

# OCR settings
OCR_GLOBAL_CONCURRENCY = 1
PDF_OCR_MIN_TEXT_CHARS = 25
PDF_OCR_RENDER_DPI = 100
PDF_PAGE_CACHE_SUBDIR = "pdf_pages"
ATTACHMENT_SUSPICIOUS_CHAR_THRESHOLD = int(os.environ.get("ATTACHMENT_SUSPICIOUS_CHAR_THRESHOLD", "40"))
ATTACHMENT_SUSPICIOUS_MAX_COUNT = int(os.environ.get("ATTACHMENT_SUSPICIOUS_MAX_COUNT", "12"))

# Schema generation settings
SCHEMA_DEFAULT_SAMPLE_SIZE = 10
SCHEMA_DEFAULT_HEAD_SIZE = 5
SCHEMA_MODEL_ID = "gemini-3-flash-preview"
SCHEMA_THINKING_LEVEL = "MINIMAL"
SCHEMA_REQUEST_TIMEOUT = 300.0

# Analysis settings
ANALYSIS_MODEL_ID = "gemini-3-flash-preview"
ANALYSIS_THINKING_LEVEL = "MINIMAL"
ANALYSIS_BATCH_SIZE = 5
ANALYSIS_REQUEST_TIMEOUT = 300.0
ANALYSIS_JSON_FILENAME = "analysis.json"
ANALYSIS_CSV_FILENAME = "analysis.csv"

# Post-processing settings
POST_PROCESSING_SUBDIR = "post-processing"
TAG_FIX_DEDUPED_CSV_FILENAME = "analysis_deduped.csv"
TAG_FIX_MAPPINGS_FILENAME = "mappings.json"
TAG_FIX_STREAM_CHUNK_SIZE = 500

# Token usage tracking
TOKEN_USAGE_FILE = Path(os.environ.get("TOKEN_USAGE_FILE", str(DATA_DIR / "token_usage.jsonl")))

# Logging format
LOG_FORMAT = "%(asctime)s.%(msecs)03d [%(levelname)s] %(message)s"
LOG_DATE_FORMAT = "%H:%M:%S"
