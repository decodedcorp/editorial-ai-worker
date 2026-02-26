"""Pipeline observability logs endpoint."""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException

from editorial_ai.api.deps import verify_api_key
from editorial_ai.api.schemas import (
    LogsResponse,
    NodeRunLogResponse,
    PipelineRunSummaryResponse,
    TokenUsageResponse,
)
from editorial_ai.observability.models import PipelineRunSummary
from editorial_ai.observability.storage import read_node_logs
from editorial_ai.services.content_service import get_content_by_id

logger = logging.getLogger(__name__)

router = APIRouter(dependencies=[Depends(verify_api_key)])


@router.get("/{content_id}/logs", response_model=LogsResponse)
async def get_content_logs(content_id: str, include_io: bool = True):
    """Return node-level execution logs for a content's pipeline run.

    Query params:
        include_io: When False, input_state and output_state are excluded
                    from the response to reduce payload size.
    """
    # 1. Resolve content_id -> thread_id
    content = await get_content_by_id(content_id)
    if content is None:
        raise HTTPException(status_code=404, detail="Content not found")

    thread_id: str = content["thread_id"]

    # 2. Read node logs from JSONL storage
    node_logs = read_node_logs(thread_id)

    # 3. Sort chronologically
    node_logs.sort(key=lambda log: log.started_at)

    # 4. Convert to response models
    runs: list[NodeRunLogResponse] = []
    for log in node_logs:
        token_usage_resp = [
            TokenUsageResponse(
                prompt_tokens=tu.prompt_tokens,
                completion_tokens=tu.completion_tokens,
                total_tokens=tu.total_tokens,
                model_name=tu.model_name,
            )
            for tu in log.token_usage
        ]

        runs.append(
            NodeRunLogResponse(
                node_name=log.node_name,
                status=log.status,
                started_at=log.started_at,
                ended_at=log.ended_at,
                duration_ms=log.duration_ms,
                token_usage=token_usage_resp,
                total_prompt_tokens=log.total_prompt_tokens,
                total_completion_tokens=log.total_completion_tokens,
                total_tokens=log.total_tokens,
                prompt_chars=log.prompt_chars,
                error_type=log.error_type,
                error_message=log.error_message,
                input_state=log.input_state if include_io else None,
                output_state=log.output_state if include_io else None,
            )
        )

    # 5. Build summary if logs exist
    summary: PipelineRunSummaryResponse | None = None
    if runs:
        agg = PipelineRunSummary.from_logs(thread_id, node_logs)
        summary = PipelineRunSummaryResponse(
            thread_id=agg.thread_id,
            node_count=agg.node_count,
            total_duration_ms=agg.total_duration_ms,
            total_prompt_tokens=agg.total_prompt_tokens,
            total_completion_tokens=agg.total_completion_tokens,
            total_tokens=agg.total_tokens,
            status=agg.status,
            started_at=agg.started_at,
            ended_at=agg.ended_at,
        )

    return LogsResponse(
        content_id=content_id,
        thread_id=thread_id,
        runs=runs,
        summary=summary,
    )
