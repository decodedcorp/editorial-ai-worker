"""Publish node that finalizes approved content in Supabase.

Updates the content status from approved to published and sets pipeline_status.
"""

from __future__ import annotations

import logging

from editorial_ai.services.content_service import update_content_status
from editorial_ai.state import EditorialPipelineState

logger = logging.getLogger(__name__)


async def publish_node(state: EditorialPipelineState) -> dict:
    """Finalize approved content by updating status to published.

    Reads content_id from state (set by admin_gate on approval)
    and updates the Supabase row to published status.
    """
    content_id = state.get("current_draft_id")

    if not content_id:
        logger.error("publish_node called without current_draft_id in state")
        return {
            "pipeline_status": "failed",
            "error_log": ["publish_node: missing current_draft_id"],
        }

    await update_content_status(content_id, "published")
    logger.info("Content published: content_id=%s", content_id)

    return {"pipeline_status": "published"}
