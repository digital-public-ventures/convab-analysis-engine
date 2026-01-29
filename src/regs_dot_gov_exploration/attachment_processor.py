"""Attachment processing utilities for extracting text from PDF and DOCX files.

This module handles downloading and extracting text from document attachments,
supporting both HTTP URLs and local file paths.
"""

import io
from pathlib import Path
from typing import Protocol
from urllib.parse import urlparse

import httpx


class DocumentExtractor(Protocol):
    """Protocol for document text extractors."""

    def extract(self, content: bytes) -> str:
        """Extract text from document bytes."""
        ...


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
            raise ImportError(
                "pymupdf is required for PDF extraction. Install with: uv add pymupdf"
            ) from err

        text_parts = []
        with fitz.open(stream=content, filetype="pdf") as doc:
            for page in doc:
                text_parts.append(page.get_text())

        return "\n".join(text_parts)


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
            raise ImportError(
                "python-docx is required for DOCX extraction. Install with: uv add python-docx"
            ) from err

        doc = Document(io.BytesIO(content))
        paragraphs = [para.text for para in doc.paragraphs]
        return "\n".join(paragraphs)


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

    def __init__(self, timeout: float = 30.0):
        """Initialize the attachment processor.

        Args:
            timeout: HTTP request timeout in seconds
        """
        self.timeout = timeout
        self._extractor_instances: dict[str, DocumentExtractor] = {}

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
        """Fetch content from a URL.

        Args:
            url: HTTP/HTTPS URL

        Returns:
            Raw file content as bytes

        Raises:
            httpx.HTTPError: If the request fails
        """
        # Use headers to mimic a browser request (some gov sites require this)
        headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
            "Accept": (
                "application/pdf,"
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document,*/*"
            ),
        }

        with httpx.Client(timeout=self.timeout, follow_redirects=True, headers=headers) as client:
            response = client.get(url)
            response.raise_for_status()
            content: bytes = response.content
            return content

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

    def extract_text(self, url_or_path: str) -> str:
        """Extract text from a document at the given URL or path.

        Args:
            url_or_path: HTTP URL or local file path to a PDF or DOCX

        Returns:
            Extracted text content

        Raises:
            ValueError: If file type is not supported
            httpx.HTTPError: If URL fetch fails
            FileNotFoundError: If local file doesn't exist
        """
        # Detect file type
        extension = self._detect_extension(url_or_path)
        extractor = self._get_extractor(extension)

        # Fetch or read content
        if self._is_url(url_or_path):
            print(f"Fetching: {url_or_path}")
            content = self._fetch_url(url_or_path)
        else:
            print(f"Reading: {url_or_path}")
            content = self._read_file(url_or_path)

        # Extract text
        return extractor.extract(content)

    def extract_text_safe(self, url_or_path: str) -> tuple[str | None, str | None]:
        """Extract text with error handling.

        Args:
            url_or_path: HTTP URL or local file path

        Returns:
            Tuple of (extracted_text, error_message).
            If successful, error_message is None.
            If failed, extracted_text is None.
        """
        try:
            text = self.extract_text(url_or_path)
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

    def process_attachments(
        self,
        urls: list[str],
        skip_errors: bool = True,
    ) -> dict[str, str | None]:
        """Process multiple attachments and extract text from each.

        Args:
            urls: List of URLs or file paths
            skip_errors: If True, continue processing on errors. If False, raise on first error.

        Returns:
            Dictionary mapping URL/path to extracted text (or None if extraction failed)
        """
        results: dict[str, str | None] = {}

        for url in urls:
            text, error = self.extract_text_safe(url)
            if error:
                print(f"Warning: {error}")
                if not skip_errors:
                    raise RuntimeError(error)

            results[url] = text

        return results


def combine_narratives(
    inline_comment: str,
    attachment_texts: dict[str, str | None],
    separator: str = "\n\n---\n\n",
) -> str:
    """Combine inline comment with extracted attachment text.

    Args:
        inline_comment: The inline comment text from the CSV
        attachment_texts: Dictionary of URL -> extracted text
        separator: Separator between sections

    Returns:
        Combined narrative text
    """
    parts = []

    # Add inline comment if present
    if inline_comment and inline_comment.strip():
        parts.append(f"[Inline Comment]\n{inline_comment.strip()}")

    # Add attachment texts
    for url, text in attachment_texts.items():
        if text and text.strip():
            # Extract filename from URL for labeling
            filename = Path(urlparse(url).path).name
            parts.append(f"[Attachment: {filename}]\n{text.strip()}")

    return separator.join(parts) if parts else ""
