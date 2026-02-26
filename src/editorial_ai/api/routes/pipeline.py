"""Pipeline trigger and status endpoints."""

from __future__ import annotations

import asyncio
import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException
from langgraph.graph.state import CompiledStateGraph

from editorial_ai.api.deps import get_graph, verify_api_key
from editorial_ai.api.routes.sources import (
    _fetch_celebs_by_ids,
    _fetch_posts_by_ids,
    _fetch_products_by_ids,
    _build_curated_topics,
)
from editorial_ai.api.schemas import TriggerRequest, TriggerResponse
from editorial_ai.services.supabase_client import get_supabase_client

logger = logging.getLogger(__name__)

router = APIRouter(dependencies=[Depends(verify_api_key)])


async def _resolve_db_sources(body: TriggerRequest) -> dict:
    """Resolve selected DB source IDs into pipeline-ready state."""
    client = await get_supabase_client()

    posts = await _fetch_posts_by_ids(client, body.selected_posts or [])
    celebs = await _fetch_celebs_by_ids(client, body.selected_celebs or [])
    products = await _fetch_products_by_ids(client, body.selected_products or [])
    curated_topics = _build_curated_topics(posts, celebs, products, body.category)

    return {
        "curated_topics": curated_topics,
        "enriched_contexts": posts,
    }


@router.post("/trigger", response_model=TriggerResponse)
async def trigger_pipeline(
    body: TriggerRequest,
    graph: CompiledStateGraph = Depends(get_graph),
):
    """Start a new pipeline run. Returns immediately with thread_id for polling."""
    thread_id = str(uuid.uuid4())
    config = {"configurable": {"thread_id": thread_id}}

    # Build initial state based on mode
    if body.mode == "db_source":
        # Resolve DB sources before launching pipeline
        db_data = await _resolve_db_sources(body)
        initial_state = {
            "thread_id": thread_id,
            "curation_input": {
                "seed_keyword": body.seed_keyword,
                "category": body.category,
                "tone": body.tone,
                "style": body.style,
                "mode": "db_source",
            },
            # Pre-populated from DB — curation and source nodes will skip
            "curated_topics": db_data["curated_topics"],
            "enriched_contexts": db_data["enriched_contexts"],
        }
    elif body.mode == "ai_db_search":
        initial_state = {
            "thread_id": thread_id,
            "curation_input": {
                "seed_keyword": body.seed_keyword,
                "category": body.category,
                "tone": body.tone,
                "style": body.style,
                "mode": "ai_db_search",
            },
        }
    else:
        initial_state = {
            "thread_id": thread_id,
            "curation_input": {
                "seed_keyword": body.seed_keyword,
                "category": body.category,
                "tone": body.tone,
                "style": body.style,
                "target_celeb": body.target_celeb,
                "target_brand": body.target_brand,
            },
        }

    async def _run_pipeline() -> None:
        try:
            await graph.ainvoke(initial_state, config=config)
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
