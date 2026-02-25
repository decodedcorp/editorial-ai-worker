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
