"""Tests for PaddleOCR helpers."""

from __future__ import annotations

from typing import Any

from app.processing.attachment import _extract_text_from_ocr_results, _run_ocr


def test_extract_text_from_ocr_results_expected_format() -> None:
    results = [
        [
            ([[0, 0], [10, 0], [10, 10], [0, 10]], ("Hello", 0.99)),
            ([[0, 20], [10, 20], [10, 30], [0, 30]], ("World", 0.98)),
        ],
        [
            ([[0, 40], [10, 40], [10, 50], [0, 50]], ("Second", 0.97)),
        ],
    ]

    assert _extract_text_from_ocr_results(results) == "Hello\nWorld\nSecond"


def test_extract_text_from_ocr_results_non_list() -> None:
    assert _extract_text_from_ocr_results({"unexpected": "format"}) == ""


def test_run_ocr_uses_engine_ocr() -> None:
    calls: list[dict[str, Any]] = []

    class FakeOCR:
        def ocr(self, image: object, cls: bool = False) -> list[list[tuple[object, tuple[str, float]]]]:
            calls.append({"image": image, "cls": cls})
            return [[([0, 0], ("Text", 0.9))]]

    image = object()
    assert _run_ocr(FakeOCR(), image) == "Text"
    assert calls == [{"image": image, "cls": True}]
