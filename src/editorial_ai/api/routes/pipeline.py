"""Pipeline trigger and status endpoints."""

from __future__ import annotations

import asyncio
import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException
from langgraph.graph.state import CompiledStateGraph

from editorial_ai.api.deps import get_graph, verify_api_key
from editorial_ai.api.schemas import TriggerRequest, TriggerResponse

logger = logging.getLogger(__name__)

router = APIRouter(dependencies=[Depends(verify_api_key)])


@router.post("/trigger", response_model=TriggerResponse)
async def trigger_pipeline(
    body: TriggerRequest,
    graph: CompiledStateGraph = Depends(get_graph),
):
    """Start a new pipeline run. Returns immediately with thread_id for polling."""
    thread_id = str(uuid.uuid4())
    config = {"configurable": {"thread_id": thread_id}}

    async def _run_pipeline() -> None:
        try:
            await graph.ainvoke(
                {
                    "thread_id": thread_id,
                    "curation_input": {
                        "seed_keyword": body.seed_keyword,
                        "category": body.category,
                        "tone": body.tone,
                        "style": body.style,
                        "target_celeb": body.target_celeb,
                        "target_brand": body.target_brand,
                    },
                },
                config=config,
            )
        except Exception:
            logger.exception("Pipeline failed for thread %s", thread_id)

    asyncio.create_task(_run_pipeline())

    return TriggerResponse(
        thread_id=thread_id,
        message="Pipeline started, poll /api/pipeline/status/{thread_id} for progress",
    )


@router.get("/status/{thread_id}")
async def pipeline_status(
    thread_id: str,
    graph: CompiledStateGraph = Depends(get_graph),
):
    """Return current pipeline status for progress polling."""
    config = {"configurable": {"thread_id": thread_id}}
    try:
        state = await graph.aget_state(config)
    except Exception as exc:
        raise HTTPException(
            status_code=500, detail=f"Failed to get state: {exc}"
        ) from exc

    if state is None or state.values is None:
        raise HTTPException(status_code=404, detail="Thread not found")

    values = state.values
    return {
        "thread_id": thread_id,
        "pipeline_status": values.get("pipeline_status", "unknown"),
        "error_log": values.get("error_log", []),
        "has_draft": values.get("current_draft") is not None,
    }
