"""Schema generation routes."""

from __future__ import annotations

import json
import logging

import pandas as pd
from fastapi import APIRouter, HTTPException
from fastapi import Path as PathParam

from app import server_runtime
from app.schema import SchemaGenerator
from app.server_jobs import estimate_tokens
from app.server_models import SchemaRequest, SchemaResponse

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post('/schema/{hash}', response_model=SchemaResponse)
async def generate_schema_endpoint(
    request: SchemaRequest,
    content_hash: str = PathParam(..., alias='hash'),
) -> SchemaResponse:
    """Generate a tagging schema for a previously cleaned CSV."""
    if not server_runtime.data_store.hash_exists(content_hash):
        raise HTTPException(
            status_code=404,
            detail=f"Dataset with hash '{content_hash[:12]}...' not found. Run /clean first.",
        )

    existing_schema = server_runtime.data_store.get_schema(content_hash)
    if existing_schema:
        logger.info('Schema cache hit for hash: %s...', content_hash[:12])
        with existing_schema.open(encoding='utf-8') as handle:
            schema_data = json.load(handle)
        return SchemaResponse(hash=content_hash, cached=True, schema=schema_data)

    cleaned_csv = server_runtime.data_store.get_cleaned_csv(content_hash)
    if not cleaned_csv:
        raise HTTPException(
            status_code=404,
            detail=f"Cleaned CSV not found for hash '{content_hash[:12]}...'. Run /clean first.",
        )

    logger.debug('Reading cleaned CSV: %s', cleaned_csv)
    df = pd.read_csv(cleaned_csv)

    head_rows = df.head(request.num_head_rows).to_dict('records')
    remaining_df = df.iloc[request.num_head_rows :]
    sample_count = min(request.num_sample_rows, len(remaining_df))
    random_rows = remaining_df.sample(n=sample_count).to_dict('records') if sample_count > 0 else []

    max_sample_tokens = 50_000
    token_count = estimate_tokens(head_rows + random_rows)
    while token_count > max_sample_tokens and random_rows:
        random_rows.pop()
        token_count = estimate_tokens(head_rows + random_rows)

    sample_data = head_rows + random_rows
    logger.info(
        'Sampled %d rows for schema generation (head=%d, random=%d, estimated_tokens=%d)',
        len(sample_data),
        len(head_rows),
        len(random_rows),
        token_count,
    )

    try:
        generator = SchemaGenerator()
        schema = await generator.generate_schema(sample_data, request.use_case)
    except ValueError as exc:
        raise HTTPException(status_code=500, detail=f'Schema generation failed: {exc}') from exc
    except Exception as exc:
        logger.exception('Schema generation error')
        raise HTTPException(status_code=500, detail=f'Schema generation failed: {exc}') from exc

    paths = server_runtime.data_store.ensure_hash_dirs(content_hash)
    generator.save_schema(
        schema=schema,
        schema_dir=paths['schema'],
        use_case=request.use_case,
        rows_sampled=len(sample_data),
    )

    return SchemaResponse(hash=content_hash, cached=False, schema=schema)
