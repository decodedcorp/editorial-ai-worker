"""Pydantic request/response models for the admin API."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class ContentResponse(BaseModel):
    """Single content entry returned by the API."""

    id: str
    thread_id: str
    status: str
    title: str
    keyword: str
    layout_json: dict
    review_summary: str | None = None
    rejection_reason: str | None = None
    admin_feedback: str | None = None
    created_at: datetime
    updated_at: datetime
    published_at: datetime | None = None


class ContentListResponse(BaseModel):
    """Paginated list of content entries."""

    items: list[ContentResponse]
    total: int


class ApproveRequest(BaseModel):
    """Request body for approving content."""

    feedback: str | None = None


class RejectRequest(BaseModel):
    """Request body for rejecting content. Reason is required."""

    reason: str


class TriggerRequest(BaseModel):
    """Request body for triggering a new pipeline run."""

    seed_keyword: str
    category: str = "fashion"
    tone: str | None = None
    style: str | None = None
    target_celeb: str | None = None
    target_brand: str | None = None


class TriggerResponse(BaseModel):
    """Response after triggering a pipeline run."""

    thread_id: str
    message: str


class ErrorResponse(BaseModel):
    """Standard error response."""

    detail: str


# --- Observability log response models ---


class TokenUsageResponse(BaseModel):
    """Token usage from a single LLM call within a node."""

    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    model_name: str | None = None


class NodeRunLogResponse(BaseModel):
    """Per-node execution log entry."""

    node_name: str
    status: str
    started_at: datetime
    ended_at: datetime
    duration_ms: float
    token_usage: list[TokenUsageResponse]
    total_prompt_tokens: int
    total_completion_tokens: int
    total_tokens: int
    prompt_chars: int
    error_type: str | None = None
    error_message: str | None = None
    input_state: dict | None = None
    output_state: dict | None = None


class PipelineRunSummaryResponse(BaseModel):
    """Aggregated summary of an entire pipeline run."""

    thread_id: str
    node_count: int
    total_duration_ms: float
    total_prompt_tokens: int
    total_completion_tokens: int
    total_tokens: int
    status: str
    started_at: datetime | None = None
    ended_at: datetime | None = None


class LogsResponse(BaseModel):
    """Full logs response for a content's pipeline run."""

    content_id: str
    thread_id: str
    runs: list[NodeRunLogResponse]
    summary: PipelineRunSummaryResponse | None = None
