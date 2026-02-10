"""Unit tests for CLI module behavior."""

from __future__ import annotations

import runpy
import sys
from pathlib import Path

import pytest

from app import processing


def test_cli_requires_single_path_argument(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    monkeypatch.setattr(sys, "argv", ["app.cli"])

    with pytest.raises(SystemExit) as exc:
        runpy.run_module("app.cli", run_name="__main__")

    assert exc.value.code == 1
    assert "Usage: python -m app.cli <csv_file>" in capsys.readouterr().out


def test_cli_fails_when_file_missing(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    monkeypatch.setattr(sys, "argv", ["app.cli", "missing.csv"])
    monkeypatch.setattr(Path, "exists", lambda self: False)

    with pytest.raises(SystemExit) as exc:
        runpy.run_module("app.cli", run_name="__main__")

    assert exc.value.code == 1
    assert "Error: File not found:" in capsys.readouterr().out


def test_cli_prints_cleaned_output_on_success(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    async def _fake_clean_csv(path: Path) -> Path:
        return Path("/tmp/cleaned.csv")

    monkeypatch.setattr(sys, "argv", ["app.cli", "input.csv"])
    monkeypatch.setattr(Path, "exists", lambda self: True)
    monkeypatch.setattr(processing, "clean_csv", _fake_clean_csv)

    runpy.run_module("app.cli", run_name="__main__")

    output = capsys.readouterr().out
    assert "Cleaned: input.csv -> /tmp/cleaned.csv" in output


def test_cli_returns_error_when_cleaning_fails(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    async def _failing_clean_csv(path: Path) -> Path:
        raise RuntimeError("boom")

    monkeypatch.setattr(sys, "argv", ["app.cli", "input.csv"])
    monkeypatch.setattr(Path, "exists", lambda self: True)
    monkeypatch.setattr(processing, "clean_csv", _failing_clean_csv)

    with pytest.raises(SystemExit) as exc:
        runpy.run_module("app.cli", run_name="__main__")

    assert exc.value.code == 1
    assert "Error cleaning input.csv: boom" in capsys.readouterr().out
