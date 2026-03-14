"""Unit tests for the dataset CLI."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.cli import app as cli_app


def test_cli_requires_a_subcommand(capsys: pytest.CaptureFixture[str]) -> None:
    exit_code = cli_app.main([])

    captured = capsys.readouterr()
    assert exit_code == 1
    assert 'usage:' in captured.err
    assert 'clean' in captured.err
    assert 'tag-fix' in captured.err


def test_clean_command_emits_json_payload(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    async def _fake_clean_command(*, input_csv: Path, no_cache: bool, no_cache_ocr: bool) -> dict[str, object]:
        assert input_csv == Path('input.csv')
        assert no_cache is True
        assert no_cache_ocr is True
        return {
            'command': 'clean',
            'hash': 'abc123',
            'cached': False,
            'cleaned_csv': '/tmp/cleaned_input.csv',
        }

    monkeypatch.setattr(cli_app, 'run_clean_command', _fake_clean_command)

    exit_code = cli_app.main(['clean', '--input-csv', 'input.csv', '--no-cache', '--no-cache-ocr', '--json'])

    captured = capsys.readouterr()
    assert exit_code == 0
    assert json.loads(captured.out) == {
        'command': 'clean',
        'hash': 'abc123',
        'cached': False,
        'cleaned_csv': '/tmp/cleaned_input.csv',
    }


def test_schema_command_prints_human_readable_output(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    async def _fake_schema_command(
        *,
        content_hash: str,
        use_case_file: Path,
        sample_size: int,
        head_size: int,
    ) -> dict[str, object]:
        assert content_hash == 'hash123'
        assert use_case_file == Path('use_case.txt')
        assert sample_size == 9
        assert head_size == 2
        return {
            'command': 'schema',
            'hash': content_hash,
            'cached': True,
            'schema_path': '/tmp/schema.json',
            'rows_sampled': 9,
        }

    monkeypatch.setattr(cli_app, 'run_schema_command', _fake_schema_command)

    exit_code = cli_app.main(
        ['schema', '--hash', 'hash123', '--use-case-file', 'use_case.txt', '--sample-size', '9', '--head-size', '2']
    )

    captured = capsys.readouterr()
    assert exit_code == 0
    assert 'schema.hash=hash123' in captured.out
    assert 'schema.cached=True' in captured.out
    assert 'schema.schema_path=/tmp/schema.json' in captured.out


def test_analyze_command_returns_error_when_handler_fails(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    async def _failing_analyze_command(
        *,
        content_hash: str,
        use_case_file: Path,
        system_prompt_file: Path,
        no_cache: bool,
    ) -> dict[str, object]:
        raise ValueError(f'bad hash: {content_hash}')

    monkeypatch.setattr(cli_app, 'run_analyze_command', _failing_analyze_command)

    exit_code = cli_app.main(
        [
            'analyze',
            '--hash',
            'missing',
            '--use-case-file',
            'use_case.txt',
            '--system-prompt-file',
            'system_prompt.txt',
        ]
    )

    captured = capsys.readouterr()
    assert exit_code == 1
    assert captured.out == ''
    assert 'Error: bad hash: missing' in captured.err


def test_data_info_command_emits_json_payload(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    def _fake_data_info_payload(*, content_hash: str) -> dict[str, object]:
        assert content_hash == 'hash123'
        return {
            'command': 'data-info',
            'hash': content_hash,
            'has_cleaned_csv': True,
            'cleaned_file': 'cleaned_input.csv',
            'has_schema': False,
        }

    monkeypatch.setattr(cli_app, 'build_data_info_payload', _fake_data_info_payload)

    exit_code = cli_app.main(['data-info', '--hash', 'hash123', '--json'])

    captured = capsys.readouterr()
    assert exit_code == 0
    assert json.loads(captured.out) == {
        'command': 'data-info',
        'hash': 'hash123',
        'has_cleaned_csv': True,
        'cleaned_file': 'cleaned_input.csv',
        'has_schema': False,
    }


def test_tag_fix_command_dispatches_expected_flags(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    async def _fake_tag_fix_command(*, content_hash: str, no_cache: bool) -> dict[str, object]:
        assert content_hash == 'hash123'
        assert no_cache is True
        return {
            'command': 'tag-fix',
            'hash': content_hash,
            'cached': False,
            'tag_fix_csv': '/tmp/analysis_deduped.csv',
            'mappings_path': '/tmp/mappings.json',
        }

    monkeypatch.setattr(cli_app, 'run_tag_fix_command', _fake_tag_fix_command)

    exit_code = cli_app.main(['tag-fix', '--hash', 'hash123', '--no-cache'])

    captured = capsys.readouterr()
    assert exit_code == 0
    assert 'tag_fix.hash=hash123' in captured.out
    assert 'tag_fix.tag_fix_csv=/tmp/analysis_deduped.csv' in captured.out
