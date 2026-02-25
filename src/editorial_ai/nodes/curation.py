"""Curation node for the editorial pipeline graph.

Thin wrapper around CurationService: reads seed keyword from state,
calls the service, writes structured results back to state.
"""

from __future__ import annotations

import logging

from editorial_ai.services.curation_service import CurationService, get_genai_client
from editorial_ai.state import EditorialPipelineState

logger = logging.getLogger(__name__)


async def curation_node(state: EditorialPipelineState) -> dict:
    """LangGraph node: curate trending topics from a seed keyword.

    Reads state["curation_input"]["seed_keyword"], calls CurationService.curate_seed(),
    and writes curated_topics + pipeline_status back to state.
    """
    curation_input = state.get("curation_input") or {}
    keyword = curation_input.get("seed_keyword") or curation_input.get("keyword")

    if not keyword:
        return {
            "pipeline_status": "failed",
            "error_log": ["Curation failed: no seed keyword provided in curation_input"],
        }

    try:
        service = CurationService(get_genai_client())
        result = await service.curate_seed(keyword)
        return {
            "pipeline_status": "sourcing",
            "curated_topics": [t.model_dump() for t in result.topics],
        }
    except Exception as e:  # noqa: BLE001
        logger.exception("Curation node failed for keyword=%s", keyword)
        return {
            "pipeline_status": "failed",
            "error_log": [f"Curation failed: {type(e).__name__}: {e!s}"],
            "curated_topics": [],
        }
