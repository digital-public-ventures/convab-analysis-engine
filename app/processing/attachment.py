"""Attachment processing utilities for extracting text from PDF and DOCX files.

This module handles parsing, downloading, and extracting text from document attachments,
supporting both HTTP URLs and local file paths.
"""

import asyncio
import io
import logging
import os
from pathlib import Path
from typing import TYPE_CHECKING, Protocol, cast
from urllib.parse import urlparse

import httpx

from app.config import DEFAULT_TIMEOUT, IMAGE_EXTENSIONS, MAX_DOWNLOAD_CONCURRENCY

from .cache import get_cached_content, get_cached_text, save_text_to_cache, save_to_cache

logger = logging.getLogger(__name__)

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

    def extract_with_ocr(self, content: bytes, ocr_engine: "PaddleOCR") -> str:
        """Extract text from PDF bytes with OCR fallback.

        Args:
            content: Raw PDF file bytes
            ocr_engine: PaddleOCR engine instance

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

            combined_text = "\n".join(text_parts).strip()
            if combined_text:
                return combined_text

            ocr_text_parts = []
            for page in doc:
                pix = page.get_pixmap(dpi=200)
                ocr_text_parts.append(_ocr_pixmap(pix, ocr_engine))

        return "\n".join(part for part in ocr_text_parts if part)


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
    results = ocr_engine.predict(image)
    return _extract_text_from_ocr_results(results)


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
            self._ocr_engine = PaddleOCRImpl(use_textline_orientation=True, lang="en")

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

    def _is_url(self, url_or_path: str) -> bool:
        """Check if the input is a URL.

        Args:
            url_or_path: URL or file path

        Returns:
            True if it's an HTTP/HTTPS URL
        """
        parsed = urlparse(url_or_path)
        return parsed.scheme in ("http", "https")

    def _fetch_url(self, url: str) -> bytes:
        """Fetch content from a URL, using cache if available.

        Args:
            url: HTTP/HTTPS URL

        Returns:
            Raw file content as bytes

        Raises:
            httpx.HTTPError: If the request fails
        """
        # Check cache first
        if self.cache_dir:
            cached = get_cached_content(url, self.cache_dir)
            if cached is not None:
                logger.debug("CACHE HIT: %s (%d bytes)", url, len(cached))
                return cached

        # Fetch from URL
        logger.debug("FETCH START: %s", url)
        client = self._get_http_client()
        response = client.get(url)
        response.raise_for_status()
        content: bytes = response.content
        logger.debug("FETCH END: %s (%d bytes)", url, len(content))

        # Save to cache
        if self.cache_dir:
            save_to_cache(url, content, self.cache_dir)

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

    async def extract_text_async(self, url_or_path: str, use_ocr: bool = False, no_cache_ocr: bool = False) -> str:
        """Extract text from a document at the given URL or path (async).

        Args:
            url_or_path: URL or file path to extract from
            use_ocr: Whether to use OCR fallback for PDFs
            no_cache_ocr: If True, skip the extracted text cache and re-extract
                          (but still cache the new result for future use)
        """
        logger.debug("EXTRACT START: %s (no_cache_ocr=%s)", url_or_path, no_cache_ocr)

        # Check extracted text cache first (unless no_cache_ocr is set)
        if self.cache_dir and not no_cache_ocr:
            cached_text = get_cached_text(url_or_path, self.cache_dir)
            if cached_text is not None:
                logger.debug("TEXT CACHE HIT: %s (%d chars)", url_or_path, len(cached_text))
                return cached_text

        # Cache miss or no_cache_ocr - extract text
        result = await self._extract_text_uncached(url_or_path, use_ocr)

        # Cache the extracted text (always cache, even if no_cache_ocr was set)
        if self.cache_dir and result:
            save_text_to_cache(url_or_path, result, self.cache_dir)
            logger.debug("TEXT CACHED: %s", url_or_path)

        return result

    async def _extract_text_uncached(self, url_or_path: str, use_ocr: bool = False) -> str:
        """Extract text without cache lookup (internal)."""
        extension = self._detect_extension(url_or_path)
        if extension in IMAGE_EXTENSIONS:
            if self._is_url(url_or_path):
                content = await asyncio.to_thread(self._fetch_url, url_or_path)
            else:
                content = await asyncio.to_thread(self._read_file, url_or_path)

            logger.debug("OCR START: %s", url_or_path)
            result = await self._extract_image_text_async(content)
            logger.debug("OCR END: %s (%d chars)", url_or_path, len(result))
            return result

        extractor = self._get_extractor(extension)

        if self._is_url(url_or_path):
            content = await asyncio.to_thread(self._fetch_url, url_or_path)
        else:
            content = await asyncio.to_thread(self._read_file, url_or_path)

        if extension == ".pdf" and use_ocr:
            logger.debug("PDF EXTRACT START: %s", url_or_path)
            extracted = await asyncio.to_thread(extractor.extract, content)
            if extracted and extracted.strip():
                logger.debug("PDF EXTRACT END: %s (%d chars)", url_or_path, len(extracted))
                return extracted

            logger.debug("PDF OCR FALLBACK START: %s", url_or_path)
            ocr_engine = self._get_ocr_engine()
            result = await asyncio.to_thread(
                cast("PDFExtractor", extractor).extract_with_ocr,
                content,
                ocr_engine,
            )
            logger.debug("PDF OCR FALLBACK END: %s (%d chars)", url_or_path, len(result))
            return result

        logger.debug("TEXT EXTRACT START: %s", url_or_path)
        result = await asyncio.to_thread(extractor.extract, content)
        logger.debug("TEXT EXTRACT END: %s (%d chars)", url_or_path, len(result))
        return result

    async def extract_text_safe_async(
        self, url_or_path: str, use_ocr: bool = False, no_cache_ocr: bool = False
    ) -> tuple[str | None, str | None]:
        """Extract text with error handling, returning (text, error) tuple.

        Args:
            url_or_path: URL or file path to extract from
            use_ocr: Whether to use OCR fallback for PDFs
            no_cache_ocr: If True, skip the extracted text cache and re-extract

        Returns:
            Tuple of (extracted_text, None) on success, or (None, error_message) on failure
        """
        try:
            text = await self.extract_text_async(url_or_path, use_ocr=use_ocr, no_cache_ocr=no_cache_ocr)
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

    async def process_attachments_async(
        self,
        urls: list[str],
        skip_errors: bool = True,
        use_ocr: bool = False,
        max_concurrency: int | None = None,
        no_cache_ocr: bool = False,
    ) -> dict[str, str | None]:
        """Process multiple attachment URLs concurrently.

        Args:
            urls: List of URLs to process
            skip_errors: If True, continue on failures; if False, raise on first error
            use_ocr: Whether to use OCR fallback for PDFs
            max_concurrency: Maximum concurrent downloads (defaults to MAX_DOWNLOAD_CONCURRENCY)
            no_cache_ocr: If True, skip the extracted text cache and re-extract

        Returns:
            Dictionary mapping URL to extracted text (or None on failure)
        """
        results: dict[str, str | None] = {}
        if not urls:
            return results

        concurrency = max_concurrency or MAX_DOWNLOAD_CONCURRENCY
        semaphore = asyncio.Semaphore(concurrency)
        logger.debug("BATCH START: %d URLs, concurrency=%d, no_cache_ocr=%s", len(urls), concurrency, no_cache_ocr)

        completed = 0

        async def _process(url: str) -> tuple[str, str | None, str | None]:
            async with semaphore:
                text, error = await self.extract_text_safe_async(url, use_ocr=use_ocr, no_cache_ocr=no_cache_ocr)
                return url, text, error

        tasks = [asyncio.create_task(_process(url)) for url in urls]
        for task in asyncio.as_completed(tasks):
            url, text, error = await task
            completed += 1
            if error:
                logger.warning("FAILED [%d/%d]: %s - %s", completed, len(urls), url, error)
                if not skip_errors:
                    raise RuntimeError(error)
            else:
                logger.debug("DONE [%d/%d]: %s", completed, len(urls), url)
            results[url] = text

        logger.debug("BATCH END: %d URLs processed", len(results))
        return results
