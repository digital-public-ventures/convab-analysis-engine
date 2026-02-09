"""Debug helper for replaying a specific analysis batch against Gemini.

This script uses the same request construction path as the analyzer:
- _build_dynamic_batches
- _build_analysis_prompt
- _build_analysis_response_schema
- generate_structured_content

It can replay a whole batch and optionally replay each record individually.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
import unicodedata
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pandas as pd
from dotenv import load_dotenv
from google import genai

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
load_dotenv()

from app.analysis.analyzer import (
    BATCH_CHAR_BUDGET,
    _build_analysis_prompt,
    _build_analysis_response_schema,
    _build_dynamic_batches,
    _summarize_schema,
)
from app.config import ANALYSIS_BATCH_SIZE, ANALYSIS_MODEL_ID, ANALYSIS_REQUEST_TIMEOUT, ANALYSIS_THINKING_LEVEL
from app.llm.gemini_client import generate_structured_content, validate_model_config
from app.llm.rate_limiter import AsyncRateLimiter

DATA_ROOT = REPO_ROOT / 'app' / 'data'
PROMPTS_DIR = REPO_ROOT / 'app' / 'tests' / 'fixtures' / 'example_prompts'


@dataclass(frozen=True)
class DebugConfig:
    """Run configuration for a debug attempt."""

    model_id: str
    thinking_level: str
    request_timeout: float
    batch_size: int
    char_budget: int


def _default_cleaned_csv(content_hash: str) -> Path:
    cleaned_dir = DATA_ROOT / content_hash / 'cleaned_data'
    candidates = sorted(cleaned_dir.glob('cleaned_*.csv'))
    if not candidates:
        msg = f'No cleaned CSV found in {cleaned_dir}'
        raise FileNotFoundError(msg)
    return candidates[0]


def _build_records(cleaned_csv: Path) -> tuple[list[dict[str, Any]], str]:
    df = pd.read_csv(cleaned_csv)
    if df.empty:
        msg = f'Cleaned CSV is empty: {cleaned_csv}'
        raise ValueError(msg)

    id_column = str(df.columns[0])
    records: list[dict[str, Any]] = []
    for _, row in df.iterrows():
        record = row.to_dict()
        record['record_id'] = str(row[id_column])
        records.append(record)

    return records, id_column


def _select_records(
    records: list[dict[str, Any]],
    config: DebugConfig,
    batch_index: int,
    record_ids: list[str] | None,
) -> tuple[list[dict[str, Any]], list[list[dict[str, Any]]]]:
    batches = _build_dynamic_batches(
        records=records,
        max_batch_size=config.batch_size,
        char_budget=config.char_budget,
    )

    if record_ids:
        id_set = set(record_ids)
        selected = [record for record in records if str(record.get('record_id', '')) in id_set]
        missing = [rid for rid in record_ids if rid not in {str(record.get('record_id', '')) for record in selected}]
        if missing:
            msg = f'Requested record_ids not found: {missing}'
            raise ValueError(msg)
        return selected, batches

    if batch_index < 1 or batch_index > len(batches):
        msg = f'batch_index must be in [1, {len(batches)}], got {batch_index}'
        raise ValueError(msg)

    return batches[batch_index - 1], batches


def _record_stats(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    stats: list[dict[str, Any]] = []
    for record in records:
        rid = str(record.get('record_id', ''))
        comment = str(record.get('comment', ''))
        stats.append(
            {
                'record_id': rid,
                'json_chars': len(json.dumps(record)),
                'comment_chars': len(comment),
                'comment_words': len(comment.split()),
                'comment_lines': comment.count('\n') + 1,
            }
        )
    return stats


def _sanitize_text(value: str) -> str:
    normalized = unicodedata.normalize('NFKC', value)
    cleaned_chars = []
    for ch in normalized:
        if ch in ('\n', '\t'):
            cleaned_chars.append(ch)
            continue
        if unicodedata.category(ch)[0] == 'C':
            cleaned_chars.append(' ')
            continue
        cleaned_chars.append(ch)
    cleaned = ''.join(cleaned_chars)
    cleaned = cleaned.replace('\r\n', '\n').replace('\r', '\n')
    return cleaned


def _apply_text_transforms(value: str, *, newline_strategy: str, encoding_strategy: str) -> str:
    text = value
    if newline_strategy == 'normalize':
        text = text.replace('\r\n', '\n').replace('\r', '\n')
    elif newline_strategy == 'space':
        text = text.replace('\r\n', ' ').replace('\r', ' ').replace('\n', ' ')
    elif newline_strategy == 'strip':
        text = text.replace('\r', '').replace('\n', '')

    if encoding_strategy == 'ascii_ignore':
        text = text.encode('ascii', 'ignore').decode('ascii')
    elif encoding_strategy == 'ascii_replace':
        text = text.encode('ascii', 'replace').decode('ascii')

    return text


def _sanitize_record(record: dict[str, Any], *, full: bool, substring_len: int) -> dict[str, Any]:
    sanitized: dict[str, Any] = {}
    for key, value in record.items():
        if isinstance(value, str):
            text = _sanitize_text(value)
            if not full:
                text = text[:substring_len]
            sanitized[key] = text
        else:
            sanitized[key] = value
    return sanitized


async def _run_request(
    client: genai.Client,
    limiter: AsyncRateLimiter,
    prompt_text: str,
    response_schema: dict[str, Any],
    system_prompt: str,
    debug_cfg: DebugConfig,
    effective_batch_size: int,
) -> dict[str, Any]:
    started = time.monotonic()
    response_data, usage, full_response = await generate_structured_content(
        client=client,
        prompt_text=prompt_text,
        model_id=debug_cfg.model_id,
        json_schema=response_schema,
        system_instruction=system_prompt,
        thinking_level=debug_cfg.thinking_level,
        rate_limiter=limiter,
        batch_size=effective_batch_size,
        request_timeout=debug_cfg.request_timeout,
        return_full_response=True,
    )
    elapsed = time.monotonic() - started

    text = getattr(full_response, 'text', None) if full_response is not None else None
    response_records = None
    if isinstance(response_data, dict) and isinstance(response_data.get('records'), list):
        response_records = len(response_data['records'])

    return {
        'elapsed_seconds': elapsed,
        'response_records': response_records,
        'has_response_data': response_data is not None,
        'usage': usage,
        'response_text_preview': (text[:500] + '...') if isinstance(text, str) and len(text) > 500 else text,
        'response_data': response_data,
    }


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, default=str), encoding='utf-8')


async def main() -> None:
    parser = argparse.ArgumentParser(description='Replay a failing analysis batch with the same API components.')
    parser.add_argument('--hash', required=True, help='Dataset hash directory under app/data/')
    parser.add_argument('--cleaned-csv', type=Path, default=None, help='Optional override for cleaned CSV path')
    parser.add_argument('--schema-path', type=Path, default=None, help='Optional override for schema.json path')
    parser.add_argument('--use-case-path', type=Path, default=PROMPTS_DIR / 'use_case.txt')
    parser.add_argument('--system-prompt-path', type=Path, default=PROMPTS_DIR / 'system_prompt.txt')
    parser.add_argument('--batch-index', type=int, default=2, help='1-based batch index from dynamic batching')
    parser.add_argument(
        '--record-ids',
        default='',
        help='Comma-separated record IDs to debug directly (overrides --batch-index)',
    )
    parser.add_argument('--mode', choices=['batch', 'single', 'both', 'minimize'], default='both')
    parser.add_argument('--sanitize-mode', choices=['none', 'substring', 'full'], default='none')
    parser.add_argument('--substring-len', type=int, default=500)
    parser.add_argument('--newline-strategy', choices=['keep', 'normalize', 'space', 'strip'], default='keep')
    parser.add_argument('--encoding-strategy', choices=['keep', 'ascii_ignore', 'ascii_replace'], default='keep')
    parser.add_argument('--batch-size', type=int, default=ANALYSIS_BATCH_SIZE)
    parser.add_argument('--char-budget', type=int, default=BATCH_CHAR_BUDGET)
    parser.add_argument('--model-id', default=ANALYSIS_MODEL_ID)
    parser.add_argument('--thinking-level', default=ANALYSIS_THINKING_LEVEL)
    parser.add_argument('--request-timeout', type=float, default=ANALYSIS_REQUEST_TIMEOUT)
    parser.add_argument('--output-dir', type=Path, default=REPO_ROOT / 'temp' / 'debug_batch_runs')

    args = parser.parse_args()

    cleaned_csv = args.cleaned_csv or _default_cleaned_csv(args.hash)
    schema_path = args.schema_path or (DATA_ROOT / args.hash / 'schema' / 'schema.json')
    use_case = args.use_case_path.read_text(encoding='utf-8')
    system_prompt = args.system_prompt_path.read_text(encoding='utf-8')
    schema = json.loads(schema_path.read_text(encoding='utf-8'))

    debug_cfg = DebugConfig(
        model_id=args.model_id,
        thinking_level=args.thinking_level,
        request_timeout=args.request_timeout,
        batch_size=args.batch_size,
        char_budget=args.char_budget,
    )

    records, id_column = _build_records(cleaned_csv)
    selected_ids = [token.strip() for token in args.record_ids.split(',') if token.strip()]
    selected_records, batches = _select_records(
        records=records,
        config=debug_cfg,
        batch_index=args.batch_index,
        record_ids=selected_ids or None,
    )
    if args.sanitize_mode == 'substring':
        selected_records = [
            _sanitize_record(record, full=False, substring_len=args.substring_len) for record in selected_records
        ]
    elif args.sanitize_mode == 'full':
        selected_records = [_sanitize_record(record, full=True, substring_len=args.substring_len) for record in selected_records]
    if args.newline_strategy != 'keep' or args.encoding_strategy != 'keep':
        transformed_records: list[dict[str, Any]] = []
        for record in selected_records:
            transformed: dict[str, Any] = {}
            for key, value in record.items():
                if isinstance(value, str):
                    transformed[key] = _apply_text_transforms(
                        value,
                        newline_strategy=args.newline_strategy,
                        encoding_strategy=args.encoding_strategy,
                    )
                else:
                    transformed[key] = value
            transformed_records.append(transformed)
        selected_records = transformed_records

    response_schema = _build_analysis_response_schema(schema)
    schema_summary = _summarize_schema(schema)

    profile = validate_model_config(debug_cfg.model_id, debug_cfg.thinking_level)
    api_key = os.environ.get('GEMINI_API_KEY')
    if not api_key:
        msg = 'GEMINI_API_KEY environment variable not set'
        raise ValueError(msg)

    client = genai.Client(api_key=api_key)
    limiter = AsyncRateLimiter(profile.rpm, profile.tpm, profile.rpd)

    now = datetime.now(tz=UTC).strftime('%Y%m%d-%H%M%S')
    run_dir = args.output_dir / f'{args.hash}-{now}'
    run_dir.mkdir(parents=True, exist_ok=True)

    meta = {
        'hash': args.hash,
        'cleaned_csv': str(cleaned_csv),
        'schema_path': str(schema_path),
        'use_case_path': str(args.use_case_path),
        'system_prompt_path': str(args.system_prompt_path),
        'id_column': id_column,
        'mode': args.mode,
        'sanitize_mode': args.sanitize_mode,
        'substring_len': args.substring_len,
        'newline_strategy': args.newline_strategy,
        'encoding_strategy': args.encoding_strategy,
        'debug_config': debug_cfg.__dict__,
        'batch_index': args.batch_index,
        'all_batch_sizes': [len(batch) for batch in batches],
        'all_batch_char_sizes': [sum(len(json.dumps(record)) for record in batch) for batch in batches],
        'selected_record_ids': [str(record.get('record_id', '')) for record in selected_records],
        'selected_record_stats': _record_stats(selected_records),
    }
    _write_json(run_dir / 'meta.json', meta)

    print(f'Run dir: {run_dir}')
    print(f'Selected records: {meta["selected_record_ids"]}')
    print(f'Selected record stats: {meta["selected_record_stats"]}')

    if args.mode in ('batch', 'both'):
        batch_prompt = _build_analysis_prompt(
            use_case=use_case,
            schema_summary=schema_summary,
            records=selected_records,
            id_column=id_column,
        )
        batch_result = await _run_request(
            client=client,
            limiter=limiter,
            prompt_text=batch_prompt,
            response_schema=response_schema,
            system_prompt=system_prompt,
            debug_cfg=debug_cfg,
            effective_batch_size=len(selected_records),
        )
        _write_json(run_dir / 'batch_result.json', batch_result)
        print(
            'Batch result:',
            json.dumps(
                {
                    'elapsed_seconds': round(batch_result['elapsed_seconds'], 2),
                    'response_records': batch_result['response_records'],
                    'has_response_data': batch_result['has_response_data'],
                }
            ),
        )

    if args.mode in ('single', 'both'):
        single_results: list[dict[str, Any]] = []
        for record in selected_records:
            rid = str(record.get('record_id', ''))
            single_prompt = _build_analysis_prompt(
                use_case=use_case,
                schema_summary=schema_summary,
                records=[record],
                id_column=id_column,
            )
            result = await _run_request(
                client=client,
                limiter=limiter,
                prompt_text=single_prompt,
                response_schema=response_schema,
                system_prompt=system_prompt,
                debug_cfg=debug_cfg,
                effective_batch_size=1,
            )
            result['record_id'] = rid
            single_results.append(result)
            print(
                'Single result:',
                json.dumps(
                    {
                        'record_id': rid,
                        'elapsed_seconds': round(result['elapsed_seconds'], 2),
                        'response_records': result['response_records'],
                        'has_response_data': result['has_response_data'],
                    }
                ),
            )
        _write_json(run_dir / 'single_results.json', {'results': single_results})

    if args.mode == 'minimize':
        if len(selected_records) != 1:
            msg = 'minimize mode requires exactly one selected record (use --record-ids with one id)'
            raise ValueError(msg)

        original_record = selected_records[0]
        original_comment = str(original_record.get('comment', ''))
        rid = str(original_record.get('record_id', ''))
        if not original_comment:
            msg = f'Record {rid} has empty comment; nothing to minimize'
            raise ValueError(msg)

        print(f'Minimizing record {rid} with comment_chars={len(original_comment)}')

        async def _probe_comment(comment_text: str) -> dict[str, Any]:
            probe_record = dict(original_record)
            probe_record['comment'] = comment_text
            prompt_text = _build_analysis_prompt(
                use_case=use_case,
                schema_summary=schema_summary,
                records=[probe_record],
                id_column=id_column,
            )
            result = await _run_request(
                client=client,
                limiter=limiter,
                prompt_text=prompt_text,
                response_schema=response_schema,
                system_prompt=system_prompt,
                debug_cfg=debug_cfg,
                effective_batch_size=1,
            )
            result['comment_chars'] = len(comment_text)
            result['success'] = bool(result['has_response_data']) and result['response_records'] == 1
            return result

        probes: list[dict[str, Any]] = []

        full_result = await _probe_comment(original_comment)
        full_result['label'] = 'full_comment'
        probes.append(full_result)
        print(
            'Probe full:',
            json.dumps(
                {
                    'comment_chars': full_result['comment_chars'],
                    'elapsed_seconds': round(full_result['elapsed_seconds'], 2),
                    'success': full_result['success'],
                }
            ),
        )

        short_len = min(args.substring_len, len(original_comment))
        short_result = await _probe_comment(original_comment[:short_len])
        short_result['label'] = f'prefix_{short_len}'
        probes.append(short_result)
        print(
            'Probe short:',
            json.dumps(
                {
                    'comment_chars': short_result['comment_chars'],
                    'elapsed_seconds': round(short_result['elapsed_seconds'], 2),
                    'success': short_result['success'],
                }
            ),
        )

        binary_search: dict[str, Any] = {
            'performed': False,
            'max_success_chars': None,
            'min_fail_chars': None,
            'attempts': [],
        }

        if not full_result['success'] and short_result['success']:
            binary_search['performed'] = True
            left = short_len
            right = len(original_comment)
            max_success = short_len
            min_fail = len(original_comment)

            while right - left > 1:
                mid = (left + right) // 2
                mid_result = await _probe_comment(original_comment[:mid])
                mid_result['label'] = f'prefix_{mid}'
                probes.append(mid_result)
                binary_search['attempts'].append(
                    {
                        'chars': mid,
                        'success': mid_result['success'],
                        'elapsed_seconds': mid_result['elapsed_seconds'],
                    }
                )
                print(
                    'Probe mid:',
                    json.dumps(
                        {
                            'comment_chars': mid,
                            'elapsed_seconds': round(mid_result['elapsed_seconds'], 2),
                            'success': mid_result['success'],
                        }
                    ),
                )
                if mid_result['success']:
                    left = mid
                    max_success = mid
                else:
                    right = mid
                    min_fail = mid

            binary_search['max_success_chars'] = max_success
            binary_search['min_fail_chars'] = min_fail

        paragraph_results: list[dict[str, Any]] = []
        paragraphs = original_comment.split('\n\n')
        if len(paragraphs) > 1:
            for idx in range(len(paragraphs)):
                candidate_paragraphs = [paragraph for j, paragraph in enumerate(paragraphs) if j != idx]
                candidate_comment = '\n\n'.join(candidate_paragraphs)
                candidate_result = await _probe_comment(candidate_comment)
                candidate_result['label'] = f'remove_paragraph_{idx + 1}'
                candidate_result['removed_paragraph_index'] = idx + 1
                candidate_result['removed_paragraph_chars'] = len(paragraphs[idx])
                paragraph_results.append(candidate_result)
                probes.append(candidate_result)
                print(
                    'Probe remove paragraph:',
                    json.dumps(
                        {
                            'removed_paragraph_index': idx + 1,
                            'comment_chars': candidate_result['comment_chars'],
                            'elapsed_seconds': round(candidate_result['elapsed_seconds'], 2),
                            'success': candidate_result['success'],
                        }
                    ),
                )

        _write_json(
            run_dir / 'minimize_results.json',
            {
                'record_id': rid,
                'original_comment_chars': len(original_comment),
                'short_probe_chars': short_len,
                'binary_search': binary_search,
                'paragraph_results': paragraph_results,
                'all_probes': probes,
            },
        )


if __name__ == '__main__':
    import asyncio

    asyncio.run(main())
