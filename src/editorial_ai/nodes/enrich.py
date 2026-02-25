"""Enrich node for the editorial pipeline graph.

Thin wrapper around enrich_service: reads current_draft from state,
calls enrich_editorial_content to search Supabase for matching celebs/products
and re-generate content with DB context, writes enriched layout back to state.
"""

from __future__ import annotations

import logging

from editorial_ai.models.layout import MagazineLayout
from editorial_ai.services.enrich_service import enrich_editorial_content
from editorial_ai.state import EditorialPipelineState

logger = logging.getLogger(__name__)


async def enrich_editorial_node(state: EditorialPipelineState) -> dict:
    """LangGraph node: enrich editorial draft with DB celeb/product data.

    Reads current_draft from state, calls enrich_service to search Supabase
    for matching celebs/products and re-generate content with DB context.
    Writes enriched layout back to current_draft.
    """
    current_draft = state.get("current_draft")
    if not current_draft:
        return {"error_log": ["Enrich skipped: no current_draft in state"]}

    try:
        layout = MagazineLayout.model_validate(current_draft)
        enriched = await enrich_editorial_content(layout)
        return {"current_draft": enriched.model_dump()}
    except Exception as e:  # noqa: BLE001
        logger.exception("Enrich node failed")
        return {"error_log": [f"Enrich failed: {type(e).__name__}: {e!s}"]}
