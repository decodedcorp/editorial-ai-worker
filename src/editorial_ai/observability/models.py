"""Observability data models for pipeline node execution tracking.

Pydantic v2 models for capturing timing, token usage, status, and IO
snapshots at the per-node level.
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, model_validator


class TokenUsage(BaseModel):
    """Token usage from a single LLM call."""

    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    model_name: str | None = None


class NodeRunLog(BaseModel):
    """Log entry for a single node execution within a pipeline run."""

    thread_id: str
    node_name: str
    status: Literal["success", "error", "skipped"]
    started_at: datetime
    ended_at: datetime
    duration_ms: float = 0.0

    # Token tracking (multiple LLM calls per node possible)
    token_usage: list[TokenUsage] = []
    total_prompt_tokens: int = 0
    total_completion_tokens: int = 0
    total_tokens: int = 0
    prompt_chars: int = 0

    # State snapshots
    input_state: dict | None = None
    output_state: dict | None = None

    # Error details
    error_type: str | None = None
    error_message: str | None = None
    error_traceback: str | None = None  # first 5 lines only

    @model_validator(mode="before")
    @classmethod
    def compute_derived_fields(cls, data: dict) -> dict:  # noqa: ANN401
        """Compute duration_ms and token sums from raw fields."""
        if not isinstance(data, dict):
            return data

        # Compute duration_ms
        started = data.get("started_at")
        ended = data.get("ended_at")
        if started and ended and "duration_ms" not in data:
            if isinstance(started, datetime) and isinstance(ended, datetime):
                data["duration_ms"] = (ended - started).total_seconds() * 1000

        # Compute token sums
        usages = data.get("token_usage", [])
        if usages:
            prompt_sum = 0
            completion_sum = 0
            total_sum = 0
            for u in usages:
                if isinstance(u, dict):
                    prompt_sum += u.get("prompt_tokens", 0)
                    completion_sum += u.get("completion_tokens", 0)
                    total_sum += u.get("total_tokens", 0)
                elif isinstance(u, TokenUsage):
                    prompt_sum += u.prompt_tokens
                    completion_sum += u.completion_tokens
                    total_sum += u.total_tokens
            if "total_prompt_tokens" not in data:
                data["total_prompt_tokens"] = prompt_sum
            if "total_completion_tokens" not in data:
                data["total_completion_tokens"] = completion_sum
            if "total_tokens" not in data:
                data["total_tokens"] = total_sum

        return data


class PipelineRunSummary(BaseModel):
    """Aggregated summary of an entire pipeline run."""

    thread_id: str
    node_count: int
    total_duration_ms: float
    total_prompt_tokens: int
    total_completion_tokens: int
    total_tokens: int
    status: Literal["completed", "failed", "running"]
    started_at: datetime | None = None
    ended_at: datetime | None = None

    @classmethod
    def from_logs(
        cls, thread_id: str, logs: list[NodeRunLog]
    ) -> PipelineRunSummary:
        """Aggregate node logs into a pipeline summary."""
        if not logs:
            return cls(
                thread_id=thread_id,
                node_count=0,
                total_duration_ms=0.0,
                total_prompt_tokens=0,
                total_completion_tokens=0,
                total_tokens=0,
                status="running",
            )

        total_duration = sum(log.duration_ms for log in logs)
        total_prompt = sum(log.total_prompt_tokens for log in logs)
        total_completion = sum(log.total_completion_tokens for log in logs)
        total_tok = sum(log.total_tokens for log in logs)

        started = min(log.started_at for log in logs)
        ended = max(log.ended_at for log in logs)

        has_error = any(log.status == "error" for log in logs)
        status: Literal["completed", "failed", "running"] = (
            "failed" if has_error else "completed"
        )

        return cls(
            thread_id=thread_id,
            node_count=len(logs),
            total_duration_ms=total_duration,
            total_prompt_tokens=total_prompt,
            total_completion_tokens=total_completion,
            total_tokens=total_tok,
            status=status,
            started_at=started,
            ended_at=ended,
        )
