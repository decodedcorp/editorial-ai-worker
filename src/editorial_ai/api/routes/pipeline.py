"""Pipeline trigger endpoint."""

from __future__ import annotations

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
    """Start a new pipeline run. Returns when the graph pauses at admin_gate interrupt."""
    thread_id = str(uuid.uuid4())
    config = {"configurable": {"thread_id": thread_id}}

    try:
        await graph.ainvoke(
            {
                "curation_input": {
                    "seed_keyword": body.seed_keyword,
                    "category": body.category,
                },
            },
            config=config,
        )
    except Exception as exc:
        logger.exception("Pipeline trigger failed for thread %s", thread_id)
        raise HTTPException(
            status_code=500, detail=f"Pipeline trigger failed: {exc}"
        ) from exc

    return TriggerResponse(
        thread_id=thread_id,
        message="Pipeline started, will pause at admin gate for approval",
    )
