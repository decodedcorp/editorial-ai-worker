"""Design spec node for the editorial pipeline graph.

Thin wrapper around DesignSpecService: extracts keyword from state,
generates a DesignSpec, writes it as a dict to state for downstream nodes.
"""

from __future__ import annotations

import logging

from editorial_ai.models.design_spec import default_design_spec
from editorial_ai.services.design_spec_service import DesignSpecService
from editorial_ai.state import EditorialPipelineState

logger = logging.getLogger(__name__)


async def design_spec_node(state: EditorialPipelineState) -> dict:
    """LangGraph node: generate a design specification from the curated keyword.

    Reads the primary keyword from curated_topics (or curation_input fallback),
    calls DesignSpecService, and returns the spec as a dict in state.

    On any failure, returns default_design_spec() to avoid crashing the pipeline.
    """
    try:
        # Extract keyword: prefer curated topic, fall back to seed keyword
        curated_topics = state.get("curated_topics") or []
        curation_input = state.get("curation_input") or {}

        if curated_topics:
            keyword = curated_topics[0].get("main_keyword") or curated_topics[0].get("keyword", "")
        else:
            keyword = curation_input.get("seed_keyword") or curation_input.get("keyword", "")

        if not keyword:
            logger.warning("No keyword found for design spec, using default")
            return {"design_spec": default_design_spec().model_dump()}

        category = curation_input.get("category")

        service = DesignSpecService()
        spec = await service.generate_spec(keyword, category)
        return {"design_spec": spec.model_dump()}

    except Exception:  # noqa: BLE001
        logger.warning("design_spec_node failed, using default", exc_info=True)
        return {"design_spec": default_design_spec().model_dump()}
