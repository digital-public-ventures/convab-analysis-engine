"""Tests for mixed-content PDF OCR behavior."""

from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace
from typing import Literal

import pytest

from app.processing import attachment as attachment_module
from app.processing.attachment import PDFExtractor


class _FakePixmap:
    def __init__(self, token: str) -> None:
        self.token = token

    def tobytes(self, _fmt: str) -> bytes:
        return f"img-{self.token}".encode()


class _FakePage:
    def __init__(self, text: str, has_images: bool, token: str) -> None:
        self._text = text
        self._has_images = has_images
        self._token = token

    def get_text(self) -> str:
        return self._text

    def get_image_info(self, hashes: bool = False, xrefs: bool = False) -> list[dict[str, str]]:
        _ = (hashes, xrefs)
        return [{"img": "1"}] if self._has_images else []

    def get_pixmap(self, dpi: int = 100) -> _FakePixmap:
        _ = dpi
        return _FakePixmap(self._token)


class _FakeDoc:
    def __init__(self, pages: list[_FakePage]) -> None:
        self._pages = pages

    def __enter__(self) -> _FakeDoc:
        return self

    def __exit__(self, exc_type: object, exc: object, tb: object) -> Literal[False]:
        _ = (exc_type, exc, tb)
        return False

    def __iter__(self):
        return iter(self._pages)


def test_pdf_mixed_ocr_uses_page_rules(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    pages = [
        _FakePage("This page has plenty of native text to keep.", False, "p0"),
        _FakePage("short", False, "p1"),
        _FakePage("This page has images but enough native text to skip OCR.", True, "p2"),
    ]
    fake_fitz = SimpleNamespace(open=lambda stream, filetype: _FakeDoc(pages))
    monkeypatch.setitem(sys.modules, "fitz", fake_fitz)
    monkeypatch.setattr(attachment_module, "_ocr_pixmap", lambda pix, _ocr: f"OCR-{pix.token}")
    monkeypatch.setattr(attachment_module, "_ocr_image_bytes", lambda content, _ocr: content.decode("utf-8"))

    extractor = PDFExtractor()
    result = extractor.extract_with_ocr(
        b"pdf-bytes",
        ocr_engine=object(),
        cache_dir=tmp_path,
        no_cache_ocr=False,
        min_text_chars=25,
        render_dpi=100,
    )
    lines = result.splitlines()
    assert lines[0] == "This page has plenty of native text to keep."
    assert "OCR-p1" in lines
    assert "This page has images but enough native text to skip OCR." in lines
    assert "OCR-p2" not in lines


def test_pdf_page_image_cache_respected_and_bypassed(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    pages = [_FakePage("tiny", False, "p0")]
    fake_fitz = SimpleNamespace(open=lambda stream, filetype: _FakeDoc(pages))
    monkeypatch.setitem(sys.modules, "fitz", fake_fitz)

    calls = {"read": 0, "write": 0, "pixmap": 0}

    def fake_get_cached(*args: object, **kwargs: object) -> bytes | None:
        _ = (args, kwargs)
        calls["read"] += 1
        return b"CACHED"

    def fake_save_cached(*args: object, **kwargs: object) -> Path:
        _ = (args, kwargs)
        calls["write"] += 1
        return tmp_path / "cached.png"

    def fake_ocr_pixmap(pix: _FakePixmap, _ocr: object) -> str:
        _ = pix
        calls["pixmap"] += 1
        return "OCR_PIXMAP"

    monkeypatch.setattr(attachment_module, "get_cached_pdf_page_image", fake_get_cached)
    monkeypatch.setattr(attachment_module, "save_pdf_page_image_to_cache", fake_save_cached)
    monkeypatch.setattr(attachment_module, "_ocr_pixmap", fake_ocr_pixmap)
    monkeypatch.setattr(attachment_module, "_ocr_image_bytes", lambda content, _ocr: content.decode("utf-8"))

    extractor = PDFExtractor()
    first = extractor.extract_with_ocr(
        b"doc",
        ocr_engine=object(),
        cache_dir=tmp_path,
        no_cache_ocr=False,
        min_text_chars=25,
        render_dpi=100,
    )
    assert first == "CACHED"
    assert calls["read"] == 1
    assert calls["pixmap"] == 0
    assert calls["write"] == 0

    calls.update({"read": 0, "write": 0, "pixmap": 0})
    second = extractor.extract_with_ocr(
        b"doc",
        ocr_engine=object(),
        cache_dir=tmp_path,
        no_cache_ocr=True,
        min_text_chars=25,
        render_dpi=100,
    )
    assert second == "OCR_PIXMAP"
    assert calls["read"] == 0
    assert calls["pixmap"] == 1
    assert calls["write"] == 1
