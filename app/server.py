"""FastAPI server setup for CSV cleaning, schema generation, and analysis."""

from __future__ import annotations

import logging
import os
from contextlib import asynccontextmanager
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import TYPE_CHECKING

from dotenv import load_dotenv
from fastapi import FastAPI

from app.config import DATA_DIR, DOWNLOADS_DIR, LOG_DATE_FORMAT, LOG_FORMAT
from app.processing import AttachmentProcessor
from app.routers.analysis import router as analysis_router
from app.routers.cleaning import router as cleaning_router
from app.routers.jobs import router as jobs_router
from app.routers.schema import router as schema_router

if TYPE_CHECKING:
    from collections.abc import AsyncIterator

load_dotenv()

logger = logging.getLogger(__name__)
__all__ = ['app']


def _configure_logging() -> None:
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    console_level_name = os.environ.get('SERVER_CONSOLE_LOG_LEVEL', 'INFO').upper()
    file_level_name = os.environ.get('SERVER_FILE_LOG_LEVEL', 'INFO').upper()
    console_level = getattr(logging, console_level_name, logging.INFO)
    file_level = getattr(logging, file_level_name, logging.INFO)

    formatter = logging.Formatter(LOG_FORMAT, datefmt=LOG_DATE_FORMAT)

    has_stream_handler = any(
        isinstance(handler, logging.StreamHandler) and not isinstance(handler, RotatingFileHandler)
        for handler in root_logger.handlers
    )
    if not has_stream_handler:
        stream_handler = logging.StreamHandler()
        stream_handler.setLevel(console_level)
        stream_handler.setFormatter(formatter)
        root_logger.addHandler(stream_handler)

    log_dir = DATA_DIR / 'logs'
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = Path(os.environ.get('SERVER_LOG_FILE', str(log_dir / 'server-analysis-debug.log')))
    log_file.parent.mkdir(parents=True, exist_ok=True)

    existing_file_handler = next(
        (
            handler
            for handler in root_logger.handlers
            if isinstance(handler, RotatingFileHandler) and Path(handler.baseFilename) == log_file
        ),
        None,
    )
    if existing_file_handler is None:
        file_handler = RotatingFileHandler(
            filename=log_file,
            maxBytes=10_000_000,
            backupCount=5,
            encoding='utf-8',
        )
        file_handler.setLevel(file_level)
        file_handler.setFormatter(formatter)
        file_handler.doRollover()
        root_logger.addHandler(file_handler)
        logger.info('File logging enabled at %s (startup rollover applied)', log_file)


_configure_logging()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Pre-warm OCR engine on startup."""
    logger.info('Starting server, pre-warming OCR engine...')
    processor = AttachmentProcessor(cache_dir=DOWNLOADS_DIR)
    # Force OCR engine initialization
    processor.get_ocr_engine()
    app.state.processor = processor
    logger.info('OCR engine ready')

    yield

    logger.info('Shutting down, closing processor...')
    processor = getattr(app.state, 'processor', None)
    if processor is not None:
        processor.close()
    app.state.processor = None


app = FastAPI(title='CSV Cleaner & Schema Generator', lifespan=lifespan)
app.include_router(cleaning_router)
app.include_router(jobs_router)
app.include_router(schema_router)
app.include_router(analysis_router)


if __name__ == '__main__':
    import uvicorn

    uvicorn.run(app, host='127.0.0.1', port=8000)
