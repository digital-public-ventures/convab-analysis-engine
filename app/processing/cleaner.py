"""CSV data cleaner utility."""

from __future__ import annotations

import logging
from collections.abc import Awaitable, Callable
from pathlib import Path
from urllib.parse import urlparse

import pandas as pd

from app.config import ATTACHMENT_EXTENSIONS, CLEANED_DATA_DIR, DOWNLOADS_DIR, UNSUPPORTED_ATTACHMENT_EXTENSIONS
from app.processing.text_normalization import normalize_text_for_llm

from .attachment import AttachmentProcessor, is_valid_url

logger = logging.getLogger(__name__)


def has_attachment_extension(value: object) -> bool:
    """Check if a string contains any attachment extension."""
    if not isinstance(value, str):
        return False
    value_lower = value.lower()
    return any(ext in value_lower for ext in ATTACHMENT_EXTENSIONS)


def is_attachment_column(series: pd.Series) -> bool:
    """Check if a column contains attachment references with valid URLs."""
    # Check if any value contains attachment extensions
    has_extension = series.astype(str).apply(has_attachment_extension).any()
    if not has_extension:
        return False

    # Check if at least one value is a valid URL
    has_valid_url = series.astype(str).apply(is_valid_url).any()
    return bool(has_valid_url)


def _is_supported_attachment_url(url: str) -> bool:
    extension = Path(urlparse(url).path).suffix.lower()
    if not extension:
        return False
    if extension not in ATTACHMENT_EXTENSIONS:
        return False
    if extension in UNSUPPORTED_ATTACHMENT_EXTENSIONS:
        return False
    return True


def _normalize_dataframe_text_columns(df: pd.DataFrame) -> tuple[pd.DataFrame, int]:
    """Normalize string fields for robust downstream model processing.

    Leaves the first column untouched to avoid changing canonical IDs.
    """
    if df.empty:
        return df, 0

    normalized_df = df.copy()
    changed_cells = 0
    id_column = normalized_df.columns[0]
    for col in normalized_df.columns:
        if col == id_column:
            continue
        if normalized_df[col].dtype != object:
            continue
        for idx, value in normalized_df[col].items():
            if not isinstance(value, str):
                continue
            normalized = normalize_text_for_llm(value)
            if normalized != value:
                normalized_df.at[idx, col] = normalized
                changed_cells += 1
    return normalized_df, changed_cells


async def clean_csv(
    input_path: str | Path,
    processor: AttachmentProcessor | None = None,
    output_dir: Path | None = None,
    downloads_dir: Path | None = None,
    chunk_size: int | None = None,
    incremental_output: bool = False,
    on_chunk: Callable[[list[dict[str, object]]], Awaitable[None]] | None = None,
    on_row_count: Callable[[int], Awaitable[None]] | None = None,
    no_cache_ocr: bool = False,
) -> Path:
    """Clean a CSV file and save to specified directory.

    Args:
        input_path: Path to the input CSV file
        processor: Optional pre-initialized AttachmentProcessor (for server use)
        output_dir: Directory for cleaned CSV output (default: CLEANED_DATA_DIR)
        downloads_dir: Directory for downloaded attachments (default: DOWNLOADS_DIR)
        chunk_size: Optional chunk size for incremental processing
        incremental_output: If True, write chunked output to a partial file and atomically finalize on completion
        on_chunk: Optional callback invoked with each cleaned chunk
        on_row_count: Optional callback invoked with total row count
        no_cache_ocr: If True, bypass OCR cache reads, force fresh OCR, and overwrite OCR caches

    Returns:
        Path to the cleaned CSV file

    Raises:
        ValueError: If first column values are not unique or CSV is empty
    """
    logger.debug("clean_csv START: %s", input_path)
    input_path = Path(input_path)
    if incremental_output and chunk_size is None:
        raise ValueError("incremental_output requires chunk_size")

    save_dir = output_dir or CLEANED_DATA_DIR
    save_dir.mkdir(parents=True, exist_ok=True)
    output_filename = f"cleaned_{input_path.name}"
    output_path = save_dir / output_filename
    partial_output_path = output_path.with_suffix(f"{output_path.suffix}.partial")
    if incremental_output:
        partial_output_path.unlink(missing_ok=True)

    effective_downloads_dir = downloads_dir or DOWNLOADS_DIR
    logger.debug(
        "clean_csv cache context: downloads_dir=%s processor_cache_dir=%s no_cache_ocr=%s",
        effective_downloads_dir,
        getattr(processor, "cache_dir", None),
        no_cache_ocr,
    )

    logger.debug("Reading CSV...")
    df = pd.read_csv(input_path)
    logger.debug("CSV read complete: %d rows, %d columns", len(df), len(df.columns))
    if on_row_count is not None:
        await on_row_count(len(df))

    if df.empty:
        raise ValueError("CSV file is empty")

    # Validate first column uniqueness
    first_col = df.columns[0]
    if df[first_col].duplicated().any():
        duplicates = df[first_col][df[first_col].duplicated()].unique().tolist()
        raise ValueError(f"First column '{first_col}' has duplicate values: {duplicates}")

    # Identify attachment columns
    logger.debug("Identifying attachment columns...")
    attachment_cols = [col for col in df.columns if is_attachment_column(df[col])]
    logger.debug("Found %d attachment columns: %s", len(attachment_cols), attachment_cols)

    cleaned_frames: list[pd.DataFrame] = []

    if chunk_size:
        owns_processor = processor is None
        if owns_processor and attachment_cols:
            cache_dir = downloads_dir or DOWNLOADS_DIR
            logger.debug("Creating AttachmentProcessor (chunked) cache_dir=%s", cache_dir)
            processor = AttachmentProcessor(cache_dir=cache_dir)
        try:
            for start in range(0, len(df), chunk_size):
                chunk_df = df.iloc[start : start + chunk_size].copy()
                chunk_df.reset_index(drop=True, inplace=True)  # Reset index for local row_idx access

                if attachment_cols:
                    chunk_url_locations: list[tuple[int, str, str]] = []
                    for col in attachment_cols:
                        for row_idx, cell in enumerate(chunk_df[col]):
                            if pd.notna(cell):
                                urls = [u.strip() for u in str(cell).split(",") if u.strip()]
                                for url in urls:
                                    if is_valid_url(url) and _is_supported_attachment_url(url):
                                        chunk_url_locations.append((row_idx, col, url))
                                    elif is_valid_url(url):
                                        logger.debug("Skipping unsupported attachment URL: %s", url)

                    unique_urls = list({loc[2] for loc in chunk_url_locations})

                    chunk_extracted_data: dict[tuple[int, str], list[str]] = {}
                    if unique_urls and processor is not None:
                        results = await processor.process_attachments_async(
                            unique_urls,
                            use_ocr=True,
                            no_cache_ocr=no_cache_ocr,
                        )
                        for row_idx, col, url in chunk_url_locations:
                            key = (row_idx, col)
                            text = results.get(url)
                            if text:
                                chunk_extracted_data.setdefault(key, []).append(text)

                    for col in attachment_cols:
                        extracted_col = f"{col}_extracted"
                        chunk_df[extracted_col] = ""
                        for row_idx in range(len(chunk_df)):
                            key = (row_idx, col)
                            if key in chunk_extracted_data:
                                chunk_df.at[row_idx, extracted_col] = "\n".join(chunk_extracted_data[key])

                chunk_df, changed_cells = _normalize_dataframe_text_columns(chunk_df)
                if changed_cells:
                    logger.debug(
                        "Normalized %d text cells in chunk starting at row %d",
                        changed_cells,
                        start,
                    )

                if incremental_output:
                    write_header = not partial_output_path.exists()
                    chunk_df.to_csv(
                        partial_output_path,
                        mode="w" if write_header else "a",
                        header=write_header,
                        index=False,
                    )
                    logger.info(
                        "CLEAN CSV CHUNK WRITTEN: file=%s mode=%s rows=%d start_row=%d",
                        partial_output_path,
                        "write" if write_header else "append",
                        len(chunk_df),
                        start,
                    )

                if on_chunk is not None:
                    await on_chunk(chunk_df.to_dict(orient="records"))

                if not incremental_output:
                    cleaned_frames.append(chunk_df)
        finally:
            if owns_processor and processor is not None:
                processor.close()
    elif attachment_cols:
        # Collect all URLs with their locations: (row_idx, col, url)
        logger.debug("Collecting URLs from attachment columns...")
        url_locations: list[tuple[int, str, str]] = []
        for col in attachment_cols:
            for row_idx, cell in enumerate(df[col]):
                if pd.notna(cell):
                    # Handle comma-separated URLs in a single cell
                    urls = [u.strip() for u in str(cell).split(",") if u.strip()]
                    for url in urls:
                        if is_valid_url(url) and _is_supported_attachment_url(url):
                            url_locations.append((row_idx, col, url))
                        elif is_valid_url(url):
                            logger.debug("Skipping unsupported attachment URL: %s", url)

        # Extract unique URLs and process all concurrently
        unique_urls = list({loc[2] for loc in url_locations})
        logger.debug("Collected %d total URLs, %d unique", len(url_locations), len(unique_urls))

        if unique_urls:
            logger.debug("Starting batch attachment processing...")
            # Use provided processor or create a new one
            owns_processor = processor is None
            if owns_processor:
                cache_dir = downloads_dir or DOWNLOADS_DIR
                logger.debug("Creating AttachmentProcessor cache_dir=%s", cache_dir)
                processor = AttachmentProcessor(cache_dir=cache_dir)
            try:
                results = await processor.process_attachments_async(
                    unique_urls,
                    use_ocr=True,
                    no_cache_ocr=no_cache_ocr,
                )
            finally:
                if owns_processor:
                    processor.close()
            logger.debug("Batch processing complete: %d results", len(results))

            # Build extracted text for each (row, col) by joining all URLs' text
            logger.debug("Mapping results to rows...")
            extracted_data: dict[tuple[int, str], list[str]] = {}
            for row_idx, col, url in url_locations:
                key = (row_idx, col)
                text = results.get(url)
                if text:
                    extracted_data.setdefault(key, []).append(text)

            # Create extracted columns
            for col in attachment_cols:
                extracted_col = f"{col}_extracted"
                df[extracted_col] = ""
                for row_idx in range(len(df)):
                    key = (row_idx, col)
                    if key in extracted_data:
                        df.at[row_idx, extracted_col] = "\n".join(extracted_data[key])
            logger.debug("Result mapping complete")

        if on_chunk is not None:
            await on_chunk(df.to_dict(orient="records"))
        cleaned_frames.append(df)
    else:
        if on_chunk is not None:
            await on_chunk(df.to_dict(orient="records"))
        cleaned_frames.append(df)

    if cleaned_frames:
        df = pd.concat(cleaned_frames, ignore_index=True)
        df, changed_cells = _normalize_dataframe_text_columns(df)
        if changed_cells:
            logger.debug("Normalized %d text cells during clean stage", changed_cells)

    if on_chunk is None and chunk_size is None:
        # Remove completely empty columns
        logger.debug("Removing empty columns...")
        df = df.dropna(axis=1, how="all")

        # Also remove columns where all values are empty strings
        df = df.loc[:, ~(df.astype(str).eq("").all())]

    # Save cleaned CSV
    if incremental_output:
        if not partial_output_path.exists():
            raise ValueError("incremental output file was not created")
        partial_output_path.replace(output_path)
        logger.info("CLEAN CSV FINALIZED: partial=%s final=%s", partial_output_path, output_path)
        logger.debug("clean_csv END: incremental output finalized at %s", output_path)
        return output_path

    logger.debug("Saving cleaned CSV...")
    df.to_csv(output_path, index=False)
    logger.debug("clean_csv END: saved to %s", output_path)

    return output_path
