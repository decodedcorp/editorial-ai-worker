"""Admin content management endpoints (list, detail, approve, reject)."""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException
from langgraph.graph.state import CompiledStateGraph
from langgraph.types import Command

from editorial_ai.api.deps import get_graph, verify_api_key
from editorial_ai.api.schemas import (
    ApproveRequest,
    ContentListResponse,
    ContentResponse,
    RejectRequest,
)
from editorial_ai.services.content_service import (
    get_content_by_id,
    list_contents,
    list_contents_count,
    update_content_status,
)

logger = logging.getLogger(__name__)

router = APIRouter(dependencies=[Depends(verify_api_key)])


@router.get("/", response_model=ContentListResponse)
async def list_all_contents(
    status: str | None = None,
    limit: int = 50,
    offset: int = 0,
):
    """List content entries, optionally filtered by status."""
    items = await list_contents(status=status, limit=limit, offset=offset)
    total = await list_contents_count(status=status)
    return ContentListResponse(
        items=[ContentResponse(**item) for item in items],
        total=total,
    )


@router.get("/{content_id}", response_model=ContentResponse)
async def get_content_detail(content_id: str):
    """Get a single content entry by ID."""
    content = await get_content_by_id(content_id)
    if content is None:
        raise HTTPException(status_code=404, detail="Content not found")
    return ContentResponse(**content)


@router.post("/{content_id}/approve", response_model=ContentResponse)
async def approve_content(
    content_id: str,
    body: ApproveRequest,
    graph: CompiledStateGraph = Depends(get_graph),
):
    """Approve content and resume the paused pipeline."""
    content = await get_content_by_id(content_id)
    if content is None:
        raise HTTPException(status_code=404, detail="Content not found")

    thread_id = content["thread_id"]
    config = {"configurable": {"thread_id": thread_id}}

    try:
        await graph.ainvoke(
            Command(resume={"decision": "approved"}),
            config=config,
        )
    except Exception as exc:
        logger.exception("Failed to resume graph for content %s", content_id)
        raise HTTPException(
            status_code=500, detail=f"Graph resume failed: {exc}"
        ) from exc

    updated = await update_content_status(
        content_id, "approved", admin_feedback=body.feedback
    )
    return ContentResponse(**updated)


@router.post("/{content_id}/reject", response_model=ContentResponse)
async def reject_content(
    content_id: str,
    body: RejectRequest,
    graph: CompiledStateGraph = Depends(get_graph),
):
    """Reject content and resume the paused pipeline with rejection."""
    content = await get_content_by_id(content_id)
    if content is None:
        raise HTTPException(status_code=404, detail="Content not found")

    thread_id = content["thread_id"]
    config = {"configurable": {"thread_id": thread_id}}

    try:
        await graph.ainvoke(
            Command(resume={"decision": "rejected", "reason": body.reason}),
            config=config,
        )
    except Exception as exc:
        logger.exception("Failed to resume graph for content %s", content_id)
        raise HTTPException(
            status_code=500, detail=f"Graph resume failed: {exc}"
        ) from exc

    updated = await update_content_status(
        content_id, "rejected", rejection_reason=body.reason
    )
    return ContentResponse(**updated)
