"""Request and response models for the router layer."""

from __future__ import annotations

from typing import Any

from pydantic import AliasChoices, BaseModel, ConfigDict, Field

from app.config import SCHEMA_DEFAULT_NUM_HEAD_ROWS, SCHEMA_DEFAULT_NUM_SAMPLE_ROWS


class JobStartResponse(BaseModel):
    """Response model for async job creation."""

    model_config = ConfigDict(populate_by_name=True)

    job_id: str
    status: str
    job_type: str
    content_hash: str | None = Field(default=None, alias='hash')
    cached: bool = False
    poll_url: str
    results_url: str


class SchemaRequest(BaseModel):
    """Request model for /schema endpoint."""

    use_case: str = Field(..., min_length=10, description='Description of intended data analysis')
    num_sample_rows: int = Field(
        default=SCHEMA_DEFAULT_NUM_SAMPLE_ROWS,
        ge=1,
        le=100,
        validation_alias=AliasChoices('num_sample_rows', 'sample_size'),
    )
    num_head_rows: int = Field(
        default=SCHEMA_DEFAULT_NUM_HEAD_ROWS,
        ge=1,
        le=20,
        validation_alias=AliasChoices('num_head_rows', 'head_size'),
    )


class SchemaResponse(BaseModel):
    """Response model for /schema endpoint."""

    model_config = ConfigDict(populate_by_name=True)

    content_hash: str = Field(..., alias='hash')
    cached: bool = False
    schema_data: dict = Field(..., alias='schema')


class DataInfoResponse(BaseModel):
    """Response model for /data/{hash} endpoint."""

    model_config = ConfigDict(populate_by_name=True)

    content_hash: str = Field(..., alias='hash')
    has_cleaned_csv: bool
    cleaned_file: str | None = None
    has_schema: bool


class AnalyzeRequest(BaseModel):
    """Request model for /analyze endpoint."""

    model_config = ConfigDict(populate_by_name=True)

    content_hash: str = Field(..., min_length=10, alias='hash', description='Hash of the cleaned dataset')
    use_case: str = Field(..., min_length=10, description='Description of intended analysis')
    system_prompt: str = Field(..., min_length=10, description='System prompt for analysis')


class AnalyzeResponse(BaseModel):
    """Response model for /analyze endpoint."""

    model_config = ConfigDict(populate_by_name=True)

    content_hash: str = Field(..., alias='hash')
    cached: bool = False
    analysis_json: dict
    analysis_csv: str


class TagDedupRequest(BaseModel):
    """Request model for /tag-fix endpoint."""

    model_config = ConfigDict(populate_by_name=True)

    content_hash: str = Field(..., min_length=10, alias='hash', description='Hash of the analyzed dataset')


class JobProgress(BaseModel):
    """Progress details for a background job."""

    completed_rows: int
    total_rows: int | None


class JobStatusResponse(BaseModel):
    """Response model for job status requests."""

    model_config = ConfigDict(populate_by_name=True)

    job_id: str
    status: str
    job_type: str
    completed: bool
    error: str | None
    progress: JobProgress
    content_hash: str | None = Field(default=None, alias='hash')


class JobResultsResponse(BaseModel):
    """Response model for job result pagination."""

    job_id: str
    rows: list[dict[str, Any]]
    next_cursor: str | None
    has_more: bool
    completed: bool
