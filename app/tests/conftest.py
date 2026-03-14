"""Shared pytest fixtures for app tests."""

import sys
from pathlib import Path

import pytest

from app import config as app_config
from app import server as app_server
from app.analysis import analyzer as analysis_analyzer
from app.processing import AttachmentProcessor
from app.processing import cleaner as processing_cleaner
from app.processing import data_store as processing_data_store
from app.routers import jobs_runner as app_jobs_runner
from app.routers import state as app_router_state
from app.schema import generator as schema_generator


@pytest.fixture
def sample_csv_content() -> bytes:
    """Sample CSV content for testing."""
    return b"""id,text,category
1,Customer complaint about late delivery,complaint
2,Love the product quality,praise
3,How do I return an item?,question
"""


@pytest.fixture
def mock_schema() -> dict:
    """Mock schema response for testing."""
    return {
        'schema_name': 'Test Schema',
        'version': '1.0',
        'description': 'Schema for testing',
        'enum_fields': [
            {
                'field_name': 'category_type',
                'required': True,
                'description': 'Type of feedback',
                'allowed_values': ['complaint', 'praise', 'question'],
                'nullable': False,
                'hint': 'Classify as exactly one type.',
            }
        ],
        'categorical_fields': [
            {
                'field_name': 'sentiment',
                'required': True,
                'description': 'Overall sentiment',
                'suggested_values': ['positive', 'negative', 'neutral'],
                'allow_multiple': False,
                'nullable': False,
                'min_items': 1,
            }
        ],
        'scalar_fields': [
            {
                'field_name': 'urgency',
                'required': True,
                'description': 'Urgency level',
                'scale_min': 0,
                'scale_max': 10,
                'scale_interpretation': '0=not urgent, 10=extremely urgent',
                'nullable': False,
            }
        ],
        'key_quotes_fields': [
            {
                'field_name': 'notable_quotes',
                'required': True,
                'description': 'Most impactful or emotionally-moving statements',
                'max_quotes': 2,
                'min_items': 1,
            }
        ],
        'text_array_fields': [
            {
                'field_name': 'mentioned_names',
                'required': True,
                'description': 'Names mentioned in the text',
                'min_items': 0,
                'nullable': False,
                'hint': 'Extract all person names mentioned.',
            }
        ],
    }


@pytest.fixture
def sample_data_records() -> list[dict]:
    """Sample data records for schema generation tests."""
    return [
        {'id': 1, 'text': 'Customer complaint about shipping delay'},
        {'id': 2, 'text': 'Positive feedback on product quality'},
        {'id': 3, 'text': 'Question about return policy'},
    ]


@pytest.fixture
def test_fixtures_dir() -> Path:
    """Path to test fixtures directory."""
    return Path(__file__).parent / 'fixtures'


@pytest.fixture
def fixture_downloads_dir(test_fixtures_dir: Path) -> Path:
    """Path to cached fixture downloads for attachment processing."""
    return test_fixtures_dir / 'downloads'


@pytest.fixture
def override_attachment_cache_dir(
    monkeypatch: pytest.MonkeyPatch,
    fixture_downloads_dir: Path,
) -> Path:
    """Force AttachmentProcessor to use the fixture downloads cache."""
    original_init = AttachmentProcessor.__init__

    def _init(self: AttachmentProcessor, *args: object, **kwargs: object) -> None:
        if 'cache_dir' in kwargs:
            kwargs['cache_dir'] = fixture_downloads_dir
        elif len(args) >= 2:
            args = list(args)
            args[1] = fixture_downloads_dir
            args = tuple(args)
        else:
            kwargs['cache_dir'] = fixture_downloads_dir
        original_init(self, *args, **kwargs)

    monkeypatch.setattr(AttachmentProcessor, '__init__', _init, raising=True)
    return fixture_downloads_dir


@pytest.fixture(autouse=True)
def override_data_dir(
    monkeypatch: pytest.MonkeyPatch,
    test_fixtures_dir: Path,
) -> Path:
    """Force app data directories to use test fixtures for all tests."""
    data_dir = test_fixtures_dir
    downloads_dir = data_dir / 'downloads'
    cleaned_dir = data_dir / 'cleaned_data'
    raw_dir = data_dir / 'raw'
    downloads_dir.mkdir(parents=True, exist_ok=True)
    cleaned_dir.mkdir(parents=True, exist_ok=True)
    raw_dir.mkdir(parents=True, exist_ok=True)

    monkeypatch.setattr(app_config, 'DATA_DIR', data_dir)
    monkeypatch.setattr(app_config, 'DOWNLOADS_DIR', downloads_dir)
    monkeypatch.setattr(app_config, 'CLEANED_DATA_DIR', cleaned_dir)
    monkeypatch.setattr(app_config, 'RAW_DATA_DIR', raw_dir)
    monkeypatch.setattr(app_config, 'TOKEN_USAGE_FILE', data_dir / 'token_usage.jsonl')

    monkeypatch.setattr(processing_data_store, 'DATA_DIR', data_dir)
    monkeypatch.setattr(processing_cleaner, 'DOWNLOADS_DIR', downloads_dir)
    monkeypatch.setattr(processing_cleaner, 'CLEANED_DATA_DIR', cleaned_dir)

    monkeypatch.setattr(app_server, 'DOWNLOADS_DIR', downloads_dir)
    app_router_state.data_store.data_dir = data_dir

    return data_dir


@pytest.fixture(autouse=True)
def override_prompt_record_chars(monkeypatch: pytest.MonkeyPatch) -> None:
    """Keep prompt record truncation small for test runs."""
    monkeypatch.setattr(analysis_analyzer, 'MAX_PROMPT_RECORD_CHARS', 500)


@pytest.fixture(autouse=True)
def override_llm_model_ids(monkeypatch: pytest.MonkeyPatch) -> None:
    """Force lower-cost model defaults for all tests."""
    schema_test_model_id = "gemini-2.5-flash-lite-preview-09-2025"
    analysis_test_model_id = "gemini-2.5-flash-lite-preview-09-2025"
    test_thinking_level = "NONE"
    monkeypatch.setattr(schema_generator, "SCHEMA_MODEL_ID", schema_test_model_id)
    monkeypatch.setattr(schema_generator, "SCHEMA_THINKING_LEVEL", test_thinking_level)
    monkeypatch.setattr(analysis_analyzer, "ANALYSIS_MODEL_ID", analysis_test_model_id)
    monkeypatch.setattr(analysis_analyzer, "ANALYSIS_THINKING_LEVEL", test_thinking_level)
    original_analyze = analysis_analyzer.analyze_dataset

    async def _analyze_with_test_model(
        request: analysis_analyzer.AnalysisRequest,
        config: analysis_analyzer.AnalysisConfig | None = None,
        on_batch=None,
        on_row_count=None,
    ):
        if config is None:
            config = analysis_analyzer.AnalysisConfig(
                model_id=analysis_test_model_id,
                thinking_level=test_thinking_level,
            )
        else:
            config = analysis_analyzer.AnalysisConfig(
                model_id=analysis_test_model_id,
                thinking_level=test_thinking_level,
                batch_size=config.batch_size,
            )
        return await original_analyze(
            request,
            config=config,
            on_batch=on_batch,
            on_row_count=on_row_count,
        )

    monkeypatch.setattr(analysis_analyzer, "analyze_dataset", _analyze_with_test_model)
    monkeypatch.setattr(app_jobs_runner, "analyze_dataset", _analyze_with_test_model)

    # Some tests import `analyze_dataset` directly, so patch those bound symbols too.
    analyze_integration_module = sys.modules.get("app.tests.test_analyze_first5_integration")
    if analyze_integration_module is not None:
        monkeypatch.setattr(analyze_integration_module, "analyze_dataset", _analyze_with_test_model)
