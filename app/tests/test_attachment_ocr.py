"""Tests for PaddleOCR helpers."""

from __future__ import annotations

import csv
import io
import threading
import time
from pathlib import Path
from typing import Any, cast
from urllib.parse import urlparse

import pytest
from PIL import Image

from app.config import OCR_GLOBAL_CONCURRENCY
from app.processing import cleaner as cleaner_module
from app.processing.attachment import AttachmentProcessor, _extract_text_from_ocr_results, _ocr_image_bytes, _run_ocr, is_valid_url
from app.processing.cache import content_hash, get_cached_text
from app.processing.cleaner import clean_csv, has_attachment_extension

FIXTURES_ROOT = Path(__file__).parent / "fixtures"
RESPONSES_CSV = FIXTURES_ROOT / "responses_100.csv"
REGRESSION_PDF = Path(
    "app/data/15bfafc41815164b0c19fa3996d72123f391d1ea740cf85b49c0f27c56aa8447/downloads/1c397ba7_attachment_1.pdf"
)
GARBLED_BASELINE_EXCERPT = """
p administration's push to expand at-will employment through the so-called "Schedule
re ule is not about efficienc or accuntability. It is a blatant power gracloake
rything he touches, Trump deflects blame, scapegoats entire communities, and denies
ty—but even proposing this policy is an insult to working people, to democracy, and tc
rumanity.
"""


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
        _extract_text_from_ocr_results(cast("Any", {"unexpected": "format"}))


def test_run_ocr_uses_engine_ocr() -> None:
    calls: list[dict[str, Any]] = []

    class FakeOCR:
        def predict(self, image: object) -> list[dict[str, Any]]:
            calls.append({"image": image})
            return [{"rec_texts": ["Text"], "rec_scores": [0.9]}]

    image = object()
    assert _run_ocr(FakeOCR(), image) == "Text"
    assert calls == [{"image": image}]


def test_ocr_image_bytes_applies_margin_and_white_flatten() -> None:
    source = Image.new("RGBA", (10, 10), (0, 0, 0, 0))
    for x in range(3, 7):
        for y in range(3, 7):
            source.putpixel((x, y), (0, 0, 0, 255))

    buffer = io.BytesIO()
    source.save(buffer, format="PNG")
    content = buffer.getvalue()

    captured_shapes: list[tuple[int, int, int]] = []
    captured_pixels: list[tuple[int, int, int]] = []

    class FakeOCR:
        def predict(self, image: object) -> list[dict[str, Any]]:
            arr = cast("Any", image)
            captured_shapes.append(tuple(arr.shape))
            captured_pixels.append(tuple(int(v) for v in arr[0, 0]))
            return [{"rec_texts": ["ok"], "rec_scores": [0.9]}]

    text = _ocr_image_bytes(content, FakeOCR())

    assert text == "ok"
    assert captured_shapes == [(70, 70, 3)]
    assert captured_pixels == [(255, 255, 255)]


@pytest.mark.asyncio
async def test_ocr_text_cache_hits_with_responses_fixture(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    url = _first_attachment_url(RESPONSES_CSV)
    processor = AttachmentProcessor(cache_dir=tmp_path)
    calls = {"count": 0}
    fake_content = b"same-doc-bytes"

    def fake_extract_text_uncached_sync(
        url_or_path: str,
        content: bytes,
        *,
        use_ocr: bool = False,
        no_cache_ocr: bool = False,
        strategy_counts: dict[str, int] | None = None,
    ) -> str:
        _ = (url_or_path, content, use_ocr, no_cache_ocr, strategy_counts)
        calls["count"] += 1
        return "FAKE OCR TEXT"

    monkeypatch.setattr(processor, "_load_content", lambda _: fake_content)
    monkeypatch.setattr(processor, "_extract_text_uncached_sync", fake_extract_text_uncached_sync)

    first = await processor.extract_text_async(url, use_ocr=True)
    second = await processor.extract_text_async(url, use_ocr=True)

    assert first == "FAKE OCR TEXT"
    assert second == "FAKE OCR TEXT"
    assert calls["count"] == 1
    assert get_cached_text(url, tmp_path, content_sha256=content_hash(fake_content)) == "FAKE OCR TEXT"


@pytest.mark.asyncio
async def test_no_cache_ocr_forces_reextract_and_overwrites_text_cache(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    url = _first_attachment_url(RESPONSES_CSV)
    processor = AttachmentProcessor(cache_dir=tmp_path)
    fake_content = b"same-doc-bytes"
    calls = {"count": 0}

    def fake_extract_text_uncached_sync(
        url_or_path: str,
        content: bytes,
        *,
        use_ocr: bool = False,
        no_cache_ocr: bool = False,
        strategy_counts: dict[str, int] | None = None,
    ) -> str:
        _ = (url_or_path, content, use_ocr, no_cache_ocr, strategy_counts)
        calls["count"] += 1
        return f"FAKE OCR TEXT {calls['count']}"

    monkeypatch.setattr(processor, "_load_content", lambda _: fake_content)
    monkeypatch.setattr(processor, "_extract_text_uncached_sync", fake_extract_text_uncached_sync)

    first = await processor.extract_text_async(url, use_ocr=True, no_cache_ocr=False)
    second = await processor.extract_text_async(url, use_ocr=True, no_cache_ocr=True)
    third = await processor.extract_text_async(url, use_ocr=True, no_cache_ocr=False)

    assert first == "FAKE OCR TEXT 1"
    assert second == "FAKE OCR TEXT 2"
    assert third == "FAKE OCR TEXT 2"
    assert calls["count"] == 2
    assert get_cached_text(url, tmp_path, content_sha256=content_hash(fake_content)) == "FAKE OCR TEXT 2"


def test_run_ocr_process_wide_guard_serializes_calls() -> None:
    active = 0
    max_active = 0
    lock = threading.Lock()

    class FakeOCR:
        def predict(self, image: object) -> list[dict[str, Any]]:
            nonlocal active, max_active
            _ = image
            with lock:
                active += 1
                max_active = max(max_active, active)
            time.sleep(0.03)
            with lock:
                active -= 1
            return [{"rec_texts": ["ok"], "rec_scores": [0.99]}]

    threads = [threading.Thread(target=_run_ocr, args=(FakeOCR(), object())) for _ in range(5)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    assert OCR_GLOBAL_CONCURRENCY == 1
    assert max_active == 1


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

    processor: Any = StubProcessor()
    monkeypatch.setattr(cleaner_module, "UNSUPPORTED_ATTACHMENT_EXTENSIONS", frozenset({".pdf"}))

    await clean_csv(
        RESPONSES_CSV,
        processor=processor,
        output_dir=tmp_path,
    )

    pdf_urls = [url for url in processor.urls if Path(urlparse(url).path).suffix.lower() == ".pdf"]

    assert pdf_urls == []


@pytest.mark.asyncio
async def test_clean_csv_uses_pdf_ocr_pipeline(tmp_path: Path) -> None:
    class StubProcessor:
        def __init__(self) -> None:
            self.use_ocr_values: list[bool] = []

        async def process_attachments_async(self, urls: list[str], **kwargs: object) -> dict[str, str | None]:
            self.use_ocr_values.append(bool(kwargs.get("use_ocr")))
            return dict.fromkeys(urls, "stub")

        def close(self) -> None:
            return None

    processor: Any = StubProcessor()
    await clean_csv(RESPONSES_CSV, processor=processor, output_dir=tmp_path)
    assert processor.use_ocr_values
    assert all(processor.use_ocr_values)


@pytest.mark.skipif(not REGRESSION_PDF.exists(), reason="Regression PDF fixture not present in workspace")
def test_pdf_ocr_regression_text_quality(tmp_path: Path) -> None:
    processor = AttachmentProcessor(cache_dir=tmp_path)
    text, error = processor.extract_text_safe(str(REGRESSION_PDF), use_ocr=True, no_cache_ocr=True)

    assert error is None
    assert text is not None

    higher_quality_phrases = [
        "To Whom It May Concern",
        "trustworthiness here is virtually nonexistent",
        "our shared humanity",
        "while protecting employers from any obligation to fairness",
        "very mechanisms that ensure nonpartisan integrity",
        "You cannot defend democracy while gutting its core institutions",
    ]

    baseline = GARBLED_BASELINE_EXCERPT
    for phrase in higher_quality_phrases:
        assert phrase in text
        assert phrase not in baseline
