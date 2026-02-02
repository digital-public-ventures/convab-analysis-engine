"""Tests for PaddleOCR helpers."""

from __future__ import annotations

import csv
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import pytest

from app.processing import cleaner as cleaner_module
from app.processing.attachment import AttachmentProcessor, _extract_text_from_ocr_results, _run_ocr, is_valid_url
from app.processing.cache import get_cached_text
from app.processing.cleaner import clean_csv, has_attachment_extension

FIXTURES_ROOT = Path(__file__).parent / "fixtures"
RESPONSES_CSV = FIXTURES_ROOT / "responses_100.csv"


def _first_attachment_url(csv_path: Path) -> str:
    with csv_path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            for value in row.values():
                if not value:
                    continue
                urls = [u.strip() for u in str(value).split(",") if u.strip()]
                for url in urls:
                    if is_valid_url(url) and has_attachment_extension(url):
                        return url
    raise AssertionError("No attachment URL found in responses_100.csv")


def test_extract_text_from_ocr_results_expected_format() -> None:
    results = [
        {"rec_texts": ["Hello", "World"], "rec_scores": [0.99, 0.98]},
        {"rec_texts": ["Second"], "rec_scores": [0.97]},
    ]

    assert _extract_text_from_ocr_results(results) == "Hello\nWorld\nSecond"


def test_extract_text_from_ocr_results_non_list() -> None:
    with pytest.raises(AttributeError):
        _extract_text_from_ocr_results({"unexpected": "format"})


def test_run_ocr_uses_engine_ocr() -> None:
    calls: list[dict[str, Any]] = []

    class FakeOCR:
        def predict(self, image: object) -> list[dict[str, Any]]:
            calls.append({"image": image})
            return [{"rec_texts": ["Text"], "rec_scores": [0.9]}]

    image = object()
    assert _run_ocr(FakeOCR(), image) == "Text"
    assert calls == [{"image": image}]


@pytest.mark.asyncio
async def test_ocr_text_cache_hits_with_responses_fixture(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    url = _first_attachment_url(RESPONSES_CSV)
    processor = AttachmentProcessor(cache_dir=tmp_path)
    calls = {"count": 0}

    async def fake_extract_text_uncached(url_or_path: str, use_ocr: bool = False) -> str:
        _ = (url_or_path, use_ocr)
        calls["count"] += 1
        return "FAKE OCR TEXT"

    monkeypatch.setattr(processor, "_extract_text_uncached", fake_extract_text_uncached)

    first = await processor.extract_text_async(url, use_ocr=True)
    second = await processor.extract_text_async(url, use_ocr=True)

    assert first == "FAKE OCR TEXT"
    assert second == "FAKE OCR TEXT"
    assert calls["count"] == 1
    assert get_cached_text(url, tmp_path) == "FAKE OCR TEXT"


@pytest.mark.asyncio
async def test_clean_csv_skips_unsupported_attachment_extensions(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class StubProcessor:
        def __init__(self) -> None:
            self.urls: list[str] = []

        async def process_attachments_async(self, urls: list[str], **_: object) -> dict[str, str | None]:
            self.urls.extend(urls)
            return dict.fromkeys(urls)

        def close(self) -> None:
            return None

    processor = StubProcessor()
    monkeypatch.setattr(cleaner_module, "UNSUPPORTED_ATTACHMENT_EXTENSIONS", frozenset({".pdf"}))

    await clean_csv(
        RESPONSES_CSV,
        processor=processor,
        output_dir=tmp_path,
    )

    pdf_urls = [url for url in processor.urls if Path(urlparse(url).path).suffix.lower() == ".pdf"]

    assert pdf_urls == []
