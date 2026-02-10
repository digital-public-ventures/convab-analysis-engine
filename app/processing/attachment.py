"""Attachment processing utilities for extracting text from PDF and DOCX files.

This module handles parsing, downloading, and extracting text from document attachments,
supporting both HTTP URLs and local file paths.
"""

import asyncio
import io
import logging
import os
import threading
import time
from pathlib import Path
from typing import TYPE_CHECKING, Protocol, cast
from urllib.parse import urlparse

import httpx

from app.config import (
    ATTACHMENT_SUSPICIOUS_CHAR_THRESHOLD,
    ATTACHMENT_SUSPICIOUS_MAX_COUNT,
    DEFAULT_TIMEOUT,
    IMAGE_EXTENSIONS,
    OCR_GLOBAL_CONCURRENCY,
    PDF_OCR_MIN_TEXT_CHARS,
    PDF_OCR_RENDER_DPI,
)

from .cache import (
    content_hash,
    get_cached_content,
    get_cached_pdf_page_image,
    get_cached_text,
    pdf_page_image_cache_path,
    save_pdf_page_image_to_cache,
    save_text_to_cache,
    save_to_cache,
    text_cache_path_from_content_hash,
    url_to_cache_path,
)

logger = logging.getLogger(__name__)
_OCR_LOCK = threading.Lock()
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)

if TYPE_CHECKING:
    import fitz
    from paddleocr import PaddleOCR


class DocumentExtractor(Protocol):
    """Protocol for document text extractors."""

    def extract(self, content: bytes) -> str:
        """Extract text from document bytes."""
        ...


def parse_attachment_urls(attachment_string: str) -> list[str]:
    """Parse comma-separated attachment URLs.

    Args:
        attachment_string: Comma-separated string of URLs

    Returns:
        List of individual URLs
    """
    if not attachment_string or not attachment_string.strip():
        return []

    urls = [url.strip() for url in attachment_string.split(",")]
    return [url for url in urls if url]


def is_valid_url(url: str) -> bool:
    """Check if a string is a valid HTTP/HTTPS URL.

    Args:
        url: String to validate

    Returns:
        True if the string is a valid HTTP or HTTPS URL
    """
    try:
        result = urlparse(url)
        return all([result.scheme in ("http", "https"), result.netloc])
    except Exception:
        return False


class PDFExtractor:
    """Extract text from PDF documents using pymupdf (fitz)."""

    def extract(self, content: bytes) -> str:
        """Extract text from PDF bytes.

        Args:
            content: Raw PDF file bytes

        Returns:
            Extracted text content
        """
        try:
            import fitz  # pymupdf
        except ImportError as err:
            raise ImportError("pymupdf is required for PDF extraction. Install with: uv add pymupdf") from err

        text_parts = []
        with fitz.open(stream=content, filetype="pdf") as doc:
            for page in doc:
                text_parts.append(page.get_text())

        return "\n".join(text_parts)

    def extract_with_ocr(
        self,
        content: bytes,
        ocr_engine: "PaddleOCR",
        *,
        cache_dir: Path | None = None,
        no_cache_ocr: bool = False,
        min_text_chars: int = PDF_OCR_MIN_TEXT_CHARS,
        render_dpi: int = PDF_OCR_RENDER_DPI,
        strategy_counts: dict[str, int] | None = None,
    ) -> str:
        """Extract text from PDF bytes with OCR fallback.

        Args:
            content: Raw PDF file bytes
            ocr_engine: PaddleOCR engine instance
            cache_dir: Optional cache directory for rendered page images
            no_cache_ocr: If True, bypass OCR cache reads and rerun OCR
            min_text_chars: OCR when page text length is below this threshold
            render_dpi: DPI to use when rendering page image

        Returns:
            Extracted text content
        """
        try:
            import fitz  # pymupdf
        except ImportError as err:
            raise ImportError("pymupdf is required for PDF extraction. Install with: uv add pymupdf") from err

        document_sha256 = content_hash(content)
        text_parts: list[str] = []
        native_pages = 0
        ocr_pages = 0
        with fitz.open(stream=content, filetype="pdf") as doc:
            for page_index, page in enumerate(doc):
                page_started_at = time.monotonic()
                native_text = page.get_text().strip()
                should_ocr = len(native_text) < min_text_chars

                if not should_ocr:
                    native_pages += 1
                    logger.debug(
                        "PDF PAGE PROCESS: page=%d strategy=native native_chars=%d elapsed_s=%.3f",
                        page_index,
                        len(native_text),
                        time.monotonic() - page_started_at,
                    )
                    if native_text:
                        text_parts.append(native_text)
                    continue

                ocr_pages += 1
                page_image_bytes: bytes | None = None
                if cache_dir and not no_cache_ocr:
                    page_image_bytes = get_cached_pdf_page_image(
                        document_sha256,
                        page_index,
                        render_dpi,
                        cache_dir,
                    )

                if page_image_bytes is not None:
                    if cache_dir is None:  # pragma: no cover - defensive guard
                        raise RuntimeError("cache_dir must be set when using cached PDF page images")
                    logger.info(
                        "ATTACHMENT CACHE HIT: type=pdf_page strategy=ocr_skip_render page=%d file=%s",
                        page_index,
                        pdf_page_image_cache_path(document_sha256, page_index, render_dpi, cache_dir),
                    )
                    page_text = _ocr_image_bytes(page_image_bytes, ocr_engine)
                else:
                    pix = page.get_pixmap(dpi=render_dpi)
                    page_text = _ocr_pixmap(pix, ocr_engine)
                    if cache_dir:
                        page_cache_path = save_pdf_page_image_to_cache(
                            document_sha256,
                            page_index,
                            render_dpi,
                            pix.tobytes("png"),
                            cache_dir,
                        )
                        logger.info(
                            "ATTACHMENT OCR PAGE: page=%d trigger=native_chars_below_threshold file=%s",
                            page_index,
                            page_cache_path,
                        )

                if page_text:
                    text_parts.append(page_text)
                logger.debug(
                    "PDF PAGE PROCESS: page=%d strategy=ocr native_chars=%d ocr_chars=%d used_cached_page=%s elapsed_s=%.3f",
                    page_index,
                    len(native_text),
                    len(page_text),
                    page_image_bytes is not None,
                    time.monotonic() - page_started_at,
                )

        if strategy_counts is not None:
            strategy_counts["native_pages"] = native_pages
            strategy_counts["ocr_pages"] = ocr_pages
        return "\n".join(part for part in text_parts if part)


class DOCXExtractor:
    """Extract text from DOCX documents using python-docx."""

    def extract(self, content: bytes) -> str:
        """Extract text from DOCX bytes.

        Args:
            content: Raw DOCX file bytes

        Returns:
            Extracted text content
        """
        try:
            from docx import Document
        except ImportError as err:
            raise ImportError("python-docx is required for DOCX extraction. Install with: uv add python-docx") from err

        doc = Document(io.BytesIO(content))
        paragraphs = [para.text for para in doc.paragraphs]
        return "\n".join(paragraphs)


def _ocr_pixmap(pixmap: "fitz.Pixmap", ocr_engine: "PaddleOCR") -> str:
    """Run OCR on a PyMuPDF pixmap."""
    try:
        import numpy as np
    except ImportError as err:
        raise ImportError("numpy is required for OCR. Install with: uv add numpy") from err

    img = np.frombuffer(pixmap.samples, dtype=np.uint8).reshape(
        pixmap.height,
        pixmap.width,
        pixmap.n,
    )
    if pixmap.n == 4:
        img = img[:, :, :3]

    return _run_ocr(ocr_engine, img)


def _ocr_image_bytes(content: bytes, ocr_engine: "PaddleOCR") -> str:
    """Run OCR on encoded image bytes."""
    try:
        import numpy as np
    except ImportError as err:
        raise ImportError("numpy is required for OCR. Install with: uv add numpy") from err

    try:
        from PIL import Image
    except ImportError as err:
        raise ImportError("pillow is required for image OCR. Install with: uv add pillow") from err

    image = Image.open(io.BytesIO(content)).convert("RGB")
    return _run_ocr(ocr_engine, np.array(image))


def _extract_text_from_ocr_results(results: list[dict]) -> str:
    """Extract text from PaddleOCR v3.x predict() results.

    IMPORTANT: This function is designed for PaddleOCR 3.x ONLY.
    DO NOT add support for other versions. If a different version is detected,
    the application should fail at startup with a clear version mismatch error.
    See _check_paddleocr_version() for version enforcement.

    PaddleOCR 3.x predict() returns: list[dict] where each dict contains:
    - 'rec_texts': list[str] - recognized text strings
    - 'rec_scores': list[float] - confidence scores

    Args:
        results: OCR results from PaddleOCR.predict()

    Returns:
        Extracted text with lines joined by newlines
    """
    if not results:
        return ""

    text_parts: list[str] = []

    for page_result in results:
        rec_texts = page_result.get("rec_texts", [])
        if isinstance(rec_texts, list):
            text_parts.extend(str(text) for text in rec_texts if text)

    return "\n".join(text_parts)


def _run_ocr(ocr_engine: "PaddleOCR", image: object) -> str:
    """Run OCR on an image using PaddleOCR v3.x predict() method.

    IMPORTANT: This function uses PaddleOCR 3.x API ONLY.
    DO NOT add fallback logic for other versions. If the API doesn't work,
    it means the wrong PaddleOCR version is installed and should be fixed
    at the dependency level, not worked around in code.

    Args:
        ocr_engine: PaddleOCR engine instance (must be v3.x)
        image: Image as numpy array

    Returns:
        Extracted text from the image

    Raises:
        AttributeError: If predict() method doesn't exist (wrong version)
    """
    started_at = time.monotonic()
    if OCR_GLOBAL_CONCURRENCY != 1:
        raise RuntimeError("OCR_GLOBAL_CONCURRENCY must be 1 to enforce process-wide OCR serialization")
    with _OCR_LOCK:
        results = ocr_engine.predict(image)
    text = _extract_text_from_ocr_results(results)
    logger.debug(
        "OCR PREDICT DONE: chars=%d elapsed_s=%.3f",
        len(text),
        time.monotonic() - started_at,
    )
    return text


class AttachmentProcessor:
    """Process document attachments from URLs or file paths.

    Supports PDF and DOCX formats, with automatic format detection.
    Works with both HTTP/HTTPS URLs and local file paths.
    """

    # Supported file extensions and their extractors
    EXTRACTORS: dict[str, type[DocumentExtractor]] = {
        ".pdf": PDFExtractor,
        ".docx": DOCXExtractor,
    }

    def __init__(self, timeout: float = DEFAULT_TIMEOUT, cache_dir: Path | None = None):
        """Initialize the attachment processor.

        Args:
            timeout: HTTP request timeout in seconds
            cache_dir: Optional directory to cache downloaded files
        """
        self.timeout = timeout
        self.cache_dir = cache_dir
        self._extractor_instances: dict[str, DocumentExtractor] = {}
        self._ocr_engine: PaddleOCR | None = None
        self._http_client: httpx.Client | None = None

    def _get_ocr_engine(self) -> "PaddleOCR":
        """Get or create a PaddleOCR engine instance.

        IMPORTANT: This method requires PaddleOCR 3.x.
        DO NOT add fallback logic for older versions. If initialization fails,
        it indicates a dependency issue that should be fixed by ensuring the
        correct PaddleOCR version is installed, not by adding version-specific
        workarounds.

        Raises:
            ImportError: If paddleocr is not installed
            RuntimeError: If PaddleOCR version is not 3.x
        """
        if self._ocr_engine is None:
            try:
                import paddleocr
                from paddleocr import PaddleOCR as PaddleOCRImpl
            except ImportError as err:
                raise ImportError("paddleocr is required for OCR. Install with: uv add paddleocr") from err

            # Enforce PaddleOCR 3.x - DO NOT add version fallbacks
            version = getattr(paddleocr, "__version__", "unknown")
            if not version.startswith("3."):
                raise RuntimeError(
                    f"PaddleOCR version 3.x is required, but version {version} is installed. "
                    f"Please run: uv add 'paddleocr>=3.0.0,<4.0.0'"
                )

            os.environ.setdefault("PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK", "True")
            self._ocr_engine = PaddleOCRImpl(
                device="cpu",
                cpu_threads=8,
                use_textline_orientation=True,
                text_detection_model_name="PP-OCRv5_mobile_det",
                text_recognition_model_name="en_PP-OCRv5_mobile_rec",
                textline_orientation_model_name="PP-LCNet_x1_0_textline_ori",
                text_det_limit_side_len=960,
            )

        return self._ocr_engine

    def get_ocr_engine(self) -> "PaddleOCR":
        """Return a shared OCR engine instance."""
        return self._get_ocr_engine()

    def set_shared_ocr_engine(self, engine: "PaddleOCR") -> None:
        """Set a pre-initialized OCR engine for reuse."""
        self._ocr_engine = engine

    def _get_extractor(self, extension: str) -> DocumentExtractor:
        """Get or create an extractor instance for the given extension.

        Args:
            extension: File extension (e.g., '.pdf')

        Returns:
            DocumentExtractor instance

        Raises:
            ValueError: If extension is not supported
        """
        extension = extension.lower()
        if extension not in self.EXTRACTORS:
            supported = ", ".join(self.EXTRACTORS.keys())
            raise ValueError(f"Unsupported file type: {extension}. Supported: {supported}")

        if extension not in self._extractor_instances:
            self._extractor_instances[extension] = self.EXTRACTORS[extension]()

        return self._extractor_instances[extension]

    def _detect_extension(self, url_or_path: str) -> str:
        """Detect file extension from URL or path.

        Args:
            url_or_path: URL or file path

        Returns:
            File extension (e.g., '.pdf')
        """
        # Parse as URL first
        parsed = urlparse(url_or_path)
        path = parsed.path if parsed.scheme else url_or_path

        # Get extension from path
        extension = Path(path).suffix.lower()
        logger.debug("DETECT EXTENSION: %s -> %s (path=%s)", url_or_path, extension, path)
        return extension

    def _extract_image_text(self, content: bytes) -> str:
        """Extract text from an image using OCR."""
        try:
            import numpy as np
        except ImportError as err:
            raise ImportError("numpy is required for OCR. Install with: uv add numpy") from err

        try:
            from PIL import Image
        except ImportError as err:
            raise ImportError("pillow is required for image OCR. Install with: uv add pillow") from err

        ocr_engine = self._get_ocr_engine()
        image = Image.open(io.BytesIO(content)).convert("RGB")
        img_array = np.array(image)

        return _run_ocr(ocr_engine, img_array)

    async def _extract_image_text_async(self, content: bytes) -> str:
        """Extract text from an image using OCR (async wrapper)."""
        return await asyncio.to_thread(self._extract_image_text, content)

    def _load_content(self, url_or_path: str) -> bytes:
        """Load bytes from URL or local path."""
        if self._is_url(url_or_path):
            return self._fetch_url(url_or_path)
        return self._read_file(url_or_path)

    def _is_url(self, url_or_path: str) -> bool:
        """Check if the input is a URL.

        Args:
            url_or_path: URL or file path

        Returns:
            True if it's an HTTP/HTTPS URL
        """
        parsed = urlparse(url_or_path)
        is_url = parsed.scheme in ("http", "https")
        logger.debug("IS URL: %s -> %s (scheme=%s)", url_or_path, is_url, parsed.scheme)
        return is_url

    def _fetch_url(self, url: str) -> bytes:
        """Fetch content from a URL, using cache if available.

        Args:
            url: HTTP/HTTPS URL

        Returns:
            Raw file content as bytes

        Raises:
            httpx.HTTPError: If the request fails
        """
        fetch_started_at = time.monotonic()
        # Check cache first
        if self.cache_dir:
            logger.debug("DOWNLOAD CACHE DIR: %s", self.cache_dir)
            cached = get_cached_content(url, self.cache_dir)
            if cached is not None:
                cache_path = url_to_cache_path(url, self.cache_dir)
                logger.info("ATTACHMENT CACHE HIT: type=download url=%s file=%s", url, cache_path)
                logger.debug(
                    "DOWNLOAD CACHE HIT: %s (%d bytes) elapsed_s=%.3f",
                    url,
                    len(cached),
                    time.monotonic() - fetch_started_at,
                )
                return cached
        else:
            logger.debug("DOWNLOAD CACHE SKIP: no cache_dir set for %s", url)

        # Fetch from URL
        logger.debug("FETCH START: %s", url)
        client = self._get_http_client()
        response = client.get(url)
        response.raise_for_status()
        content: bytes = response.content
        logger.debug(
            "FETCH END: %s (%d bytes status=%d elapsed_s=%.3f)",
            url,
            len(content),
            response.status_code,
            time.monotonic() - fetch_started_at,
        )

        # Save to cache
        if self.cache_dir:
            saved_path = save_to_cache(url, content, self.cache_dir)
            logger.info("ATTACHMENT SAVED: type=download url=%s file=%s", url, saved_path)

        return content

    def _get_http_client(self) -> httpx.Client:
        if self._http_client is None:
            headers = {
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
                "Accept": (
                    "application/pdf,application/vnd.openxmlformats-officedocument.wordprocessingml.document,*/*"
                ),
            }
            self._http_client = httpx.Client(
                timeout=self.timeout,
                follow_redirects=True,
                headers=headers,
            )
        return self._http_client

    def close(self) -> None:
        if self._http_client is not None:
            self._http_client.close()
            self._http_client = None

    def __del__(self) -> None:
        self.close()

    def _read_file(self, path: str) -> bytes:
        """Read content from a local file.

        Args:
            path: Local file path

        Returns:
            Raw file content as bytes

        Raises:
            FileNotFoundError: If the file doesn't exist
        """
        file_path = Path(path)
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {path}")

        return file_path.read_bytes()

    def _extract_text_uncached_sync(
        self,
        url_or_path: str,
        content: bytes,
        *,
        use_ocr: bool = False,
        no_cache_ocr: bool = False,
        strategy_counts: dict[str, int] | None = None,
    ) -> str:
        """Extract text without checking OCR caches."""
        extraction_started_at = time.monotonic()
        extension = self._detect_extension(url_or_path)
        if extension in IMAGE_EXTENSIONS:
            logger.debug("OCR START: %s", url_or_path)
            result = self._extract_image_text(content)
            logger.debug(
                "OCR END: %s (%d chars elapsed_s=%.3f)",
                url_or_path,
                len(result),
                time.monotonic() - extraction_started_at,
            )
            return result

        extractor = self._get_extractor(extension)
        if extension == ".pdf" and use_ocr:
            logger.debug("PDF OCR PIPELINE START: %s", url_or_path)
            ocr_engine = self._get_ocr_engine()
            result = cast("PDFExtractor", extractor).extract_with_ocr(
                content,
                ocr_engine,
                cache_dir=self.cache_dir,
                no_cache_ocr=no_cache_ocr,
                strategy_counts=strategy_counts,
            )
            logger.debug(
                "PDF OCR PIPELINE END: %s (%d chars elapsed_s=%.3f)",
                url_or_path,
                len(result),
                time.monotonic() - extraction_started_at,
            )
            return result

        logger.debug("TEXT EXTRACT START: %s", url_or_path)
        result = extractor.extract(content)
        logger.debug(
            "TEXT EXTRACT END: %s (%d chars elapsed_s=%.3f)",
            url_or_path,
            len(result),
            time.monotonic() - extraction_started_at,
        )
        return result

    def extract_text(self, url_or_path: str, use_ocr: bool = False, no_cache_ocr: bool = False) -> str:
        """Extract text from a document at the given URL or path."""
        logger.debug(
            "EXTRACT START: %s (no_cache_ocr=%s cache_dir=%s)",
            url_or_path,
            no_cache_ocr,
            self.cache_dir,
        )

        content = self._load_content(url_or_path)
        content_sha256 = content_hash(content)
        extraction_strategy = "native"

        if self.cache_dir and not no_cache_ocr:
            cached_text = get_cached_text(
                url_or_path,
                self.cache_dir,
                content_sha256=content_sha256,
            )
            if cached_text is not None:
                text_cache_path = text_cache_path_from_content_hash(content_sha256, self.cache_dir)
                logger.info(
                    "ATTACHMENT CACHE HIT: type=extracted_text strategy=skip_processing url=%s file=%s",
                    url_or_path,
                    text_cache_path,
                )
                logger.debug("TEXT CACHE HIT: %s (%d chars)", url_or_path, len(cached_text))
                return cached_text
        elif not self.cache_dir:
            logger.debug("TEXT CACHE SKIP: no cache_dir set for %s", url_or_path)
        else:
            logger.debug("TEXT CACHE BYPASS READ: no_cache_ocr=True for %s", url_or_path)

        extension = self._detect_extension(url_or_path)
        if extension in IMAGE_EXTENSIONS:
            extraction_strategy = "ocr"
        elif extension == ".pdf" and use_ocr:
            extraction_strategy = "ocr"

        strategy_counts: dict[str, int] = {}
        result = self._extract_text_uncached_sync(
            url_or_path,
            content,
            use_ocr=use_ocr,
            no_cache_ocr=no_cache_ocr,
            strategy_counts=strategy_counts,
        )
        if extension == ".pdf" and use_ocr:
            native_pages = strategy_counts.get("native_pages", 0)
            ocr_pages = strategy_counts.get("ocr_pages", 0)
            if native_pages > 0 and ocr_pages > 0:
                extraction_strategy = "mixed"
            elif native_pages > 0:
                extraction_strategy = "native"
            else:
                extraction_strategy = "ocr"

        if self.cache_dir and result:
            text_cache_path = save_text_to_cache(
                url_or_path,
                result,
                self.cache_dir,
                content_sha256=content_sha256,
            )
            logger.info(
                "ATTACHMENT SAVED: type=extracted_text strategy=%s url=%s file=%s",
                extraction_strategy,
                url_or_path,
                text_cache_path,
            )
            if no_cache_ocr:
                logger.debug("TEXT CACHE OVERWRITE: %s", url_or_path)
            else:
                logger.debug("TEXT CACHED: %s", url_or_path)

        return result

    async def extract_text_async(self, url_or_path: str, use_ocr: bool = False, no_cache_ocr: bool = False) -> str:
        """Async compatibility wrapper around sync extraction."""
        return await asyncio.to_thread(self.extract_text, url_or_path, use_ocr, no_cache_ocr)

    async def _extract_text_uncached(self, url_or_path: str, use_ocr: bool = False) -> str:
        """Async compatibility wrapper around sync uncached extraction."""
        content = await asyncio.to_thread(self._load_content, url_or_path)
        return await asyncio.to_thread(
            self._extract_text_uncached_sync,
            url_or_path,
            content,
            use_ocr=use_ocr,
            no_cache_ocr=False,
        )

    def extract_text_safe(
        self, url_or_path: str, use_ocr: bool = False, no_cache_ocr: bool = False
    ) -> tuple[str | None, str | None]:
        """Extract text with error handling, returning (text, error) tuple.

        Args:
            url_or_path: URL or file path to extract from
            use_ocr: Whether to use OCR fallback for PDFs
            no_cache_ocr: If True, bypass extracted text cache reads, re-extract, and overwrite cache

        Returns:
            Tuple of (extracted_text, None) on success, or (None, error_message) on failure
        """
        try:
            text = self.extract_text(url_or_path, use_ocr=use_ocr, no_cache_ocr=no_cache_ocr)
            return text, None
        except ImportError as e:
            return None, f"Missing dependency: {e}"
        except ValueError as e:
            return None, f"Unsupported format: {e}"
        except httpx.HTTPError as e:
            return None, f"HTTP error: {e}"
        except FileNotFoundError as e:
            return None, f"File not found: {e}"
        except Exception as e:
            return None, f"Extraction failed: {e}"

    async def extract_text_safe_async(
        self, url_or_path: str, use_ocr: bool = False, no_cache_ocr: bool = False
    ) -> tuple[str | None, str | None]:
        """Async compatibility wrapper around sync safe extraction."""
        return await asyncio.to_thread(self.extract_text_safe, url_or_path, use_ocr, no_cache_ocr)

    def process_attachments(
        self,
        urls: list[str],
        skip_errors: bool = True,
        use_ocr: bool = False,
        max_concurrency: int | None = None,
        no_cache_ocr: bool = False,
    ) -> dict[str, str | None]:
        """Process multiple attachment URLs synchronously."""
        _ = max_concurrency
        results: dict[str, str | None] = {}
        if not urls:
            return results

        logger.debug(
            "BATCH START: %d URLs, concurrency=%d, no_cache_ocr=%s",
            len(urls),
            OCR_GLOBAL_CONCURRENCY,
            no_cache_ocr,
        )
        total_chars = 0
        total_secs = 0.0
        suspicious_count = 0
        suspicious_examples: list[str] = []
        for idx, url in enumerate(urls, start=1):
            item_started_at = time.monotonic()
            text, error = self.extract_text_safe(url, use_ocr=use_ocr, no_cache_ocr=no_cache_ocr)
            elapsed_s = time.monotonic() - item_started_at
            if error:
                logger.warning("FAILED [%d/%d]: %s - %s", idx, len(urls), url, error)
                if not skip_errors:
                    raise RuntimeError(error)
            else:
                text_len = len(text.strip()) if text else 0
                total_chars += text_len
                total_secs += elapsed_s
                logger.debug(
                    "DONE [%d/%d]: %s chars=%d elapsed_s=%.3f",
                    idx,
                    len(urls),
                    url,
                    text_len,
                    elapsed_s,
                )
                if text_len <= ATTACHMENT_SUSPICIOUS_CHAR_THRESHOLD:
                    suspicious_count += 1
                    if len(suspicious_examples) < 5:
                        suspicious_examples.append(url)
                    logger.warning(
                        "SUSPICIOUS SHORT ATTACHMENT: url=%s chars=%d threshold=%d count=%d",
                        url,
                        text_len,
                        ATTACHMENT_SUSPICIOUS_CHAR_THRESHOLD,
                        suspicious_count,
                    )
                    if suspicious_count >= ATTACHMENT_SUSPICIOUS_MAX_COUNT:
                        raise RuntimeError(
                            "Too many suspiciously short attachment extracts "
                            f"({suspicious_count} <= {ATTACHMENT_SUSPICIOUS_CHAR_THRESHOLD} chars). "
                            f"Examples: {suspicious_examples}"
                        )
            results[url] = text

        success_count = sum(1 for value in results.values() if value is not None)
        avg_chars = (total_chars / success_count) if success_count else 0.0
        avg_secs = (total_secs / success_count) if success_count else 0.0
        logger.info(
            "BATCH SUMMARY: processed=%d success=%d suspicious_short=%d avg_chars=%.1f avg_seconds=%.3f",
            len(results),
            success_count,
            suspicious_count,
            avg_chars,
            avg_secs,
        )
        logger.debug("BATCH END: %d URLs processed", len(results))
        return results

    async def process_attachments_async(
        self,
        urls: list[str],
        skip_errors: bool = True,
        use_ocr: bool = False,
        max_concurrency: int | None = None,
        no_cache_ocr: bool = False,
    ) -> dict[str, str | None]:
        """Async compatibility wrapper around sync attachment processing.

        Args:
            urls: List of URLs to process
            skip_errors: If True, continue on failures; if False, raise on first error
            use_ocr: Whether to use OCR fallback for PDFs
            max_concurrency: Maximum concurrent downloads (defaults to MAX_DOWNLOAD_CONCURRENCY)
            no_cache_ocr: If True, bypass OCR cache reads, re-extract, and overwrite OCR caches

        Returns:
            Dictionary mapping URL to extracted text (or None on failure)
        """
        return await asyncio.to_thread(
            self.process_attachments,
            urls,
            skip_errors,
            use_ocr,
            max_concurrency,
            no_cache_ocr,
        )
