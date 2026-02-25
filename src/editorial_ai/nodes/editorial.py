"""Editorial node for the editorial pipeline graph.

Thin wrapper around EditorialService: reads curated_topics from state,
calls the service, writes MagazineLayout JSON back to state.
"""

from __future__ import annotations

import logging

from editorial_ai.services.curation_service import get_genai_client
from editorial_ai.services.editorial_service import EditorialService
from editorial_ai.state import EditorialPipelineState

logger = logging.getLogger(__name__)


async def editorial_node(state: EditorialPipelineState) -> dict:
    """LangGraph node: generate editorial content from curated topics.

    Reads state["curated_topics"], builds trend context, calls
    EditorialService.create_editorial(), and writes current_draft
    (MagazineLayout dict) + pipeline_status back to state.
    """
    curated_topics = state.get("curated_topics") or []

    if not curated_topics:
        return {
            "pipeline_status": "failed",
            "error_log": ["Editorial failed: no curated_topics available in state"],
            "current_draft": None,
        }

    # Build trend context from all topics
    backgrounds = []
    keywords = []
    for topic in curated_topics:
        bg = topic.get("trend_background", "")
        if bg:
            backgrounds.append(bg)
        kw = topic.get("keyword", "")
        if kw:
            keywords.append(kw)
        for rk in topic.get("related_keywords", []):
            if rk:
                keywords.append(rk)

    trend_context = "\n".join(backgrounds)
    if keywords:
        trend_context += "\nKeywords: " + ", ".join(keywords)

    # Use first topic keyword or fall back to curation_input seed keyword
    primary_keyword = curated_topics[0].get("keyword", "")
    if not primary_keyword:
        curation_input = state.get("curation_input") or {}
        primary_keyword = curation_input.get("keyword", "editorial")

    try:
        service = EditorialService(get_genai_client())
        layout = await service.create_editorial(primary_keyword, trend_context)
        return {
            "current_draft": layout.model_dump(),
            "pipeline_status": "reviewing",
        }
    except Exception as e:  # noqa: BLE001
        logger.exception("Editorial node failed for keyword=%s", primary_keyword)
        return {
            "pipeline_status": "failed",
            "error_log": [f"Editorial failed: {type(e).__name__}: {e!s}"],
            "current_draft": None,
        }
