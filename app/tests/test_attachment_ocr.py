"""Tests for PaddleOCR helpers."""

from __future__ import annotations

from typing import Any

from app.processing.attachment import _extract_text_from_ocr_results, _run_ocr


def test_extract_text_from_ocr_results_expected_format() -> None:
    results = [
        {"rec_texts": ["Hello", "World"], "rec_scores": [0.99, 0.98]},
        {"rec_texts": ["Second"], "rec_scores": [0.97]},
    ]

    assert _extract_text_from_ocr_results(results) == "Hello\nWorld\nSecond"


def test_extract_text_from_ocr_results_non_list() -> None:
    assert _extract_text_from_ocr_results({"unexpected": "format"}) == ""


def test_run_ocr_uses_engine_ocr() -> None:
    calls: list[dict[str, Any]] = []

    class FakeOCR:
        def predict(self, image: object) -> list[dict[str, Any]]:
            calls.append({"image": image})
            return [{"rec_texts": ["Text"], "rec_scores": [0.9]}]

    image = object()
    assert _run_ocr(FakeOCR(), image) == "Text"
    assert calls == [{"image": image}]
