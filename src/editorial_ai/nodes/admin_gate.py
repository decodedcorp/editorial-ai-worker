"""Admin gate node with LangGraph interrupt() for human-in-the-loop approval.

Saves content to Supabase (idempotent upsert) before interrupting, then
routes based on admin decision after resume.
"""

from __future__ import annotations

import logging

from langgraph.types import interrupt

from editorial_ai.services.content_service import (
    save_pending_content,
    update_content_status,
)
from editorial_ai.state import EditorialPipelineState

logger = logging.getLogger(__name__)


async def admin_gate(state: EditorialPipelineState) -> dict:
    """Pause pipeline for admin approval via LangGraph interrupt.

    Flow:
    1. Save content to Supabase as pending (upsert = idempotent on re-execution)
    2. Set pipeline_status to awaiting_approval
    3. Call interrupt() with snapshot for admin review
    4. On resume, branch on admin decision
    """
    current_draft = state.get("current_draft") or {}
    curation_input = state.get("curation_input") or {}
    review_result = state.get("review_result") or {}

    # Extract fields for content save
    # MagazineLayout stores title at top level
    title = current_draft.get("title", "")
    keyword = curation_input.get("seed_keyword", "")
    review_summary = review_result.get("summary", "")

    # 1. Save to Supabase (upsert on thread_id -- safe on re-execution)
    # NOTE: thread_id comes from the LangGraph config, but the node doesn't
    # have direct access to config. We use a deterministic thread identifier
    # derived from the keyword + title as a fallback. The API layer sets the
    # real thread_id when triggering the pipeline.
    # For now, use keyword as thread identifier (will be replaced by real
    # thread_id when the API layer passes it through state).
    thread_id = state.get("_thread_id", keyword or "unknown")

    saved = await save_pending_content(
        thread_id=thread_id,
        layout_json=current_draft,
        title=title,
        keyword=keyword,
        review_summary=review_summary,
    )
    content_id = saved.get("id", "")

    logger.info("Content saved as pending: content_id=%s, thread_id=%s", content_id, thread_id)

    # 2. Prepare snapshot for admin review
    snapshot = {
        "content_id": content_id,
        "title": title,
        "keyword": keyword,
        "review_summary": review_summary,
    }

    # 3. INTERRUPT -- graph pauses here
    # On initial run: raises interrupt, snapshot surfaced to caller
    # On resume: returns the Command(resume=...) value
    admin_response = interrupt(snapshot)

    # --- Everything below runs ONLY after resume ---
    decision = admin_response.get("decision", "rejected")

    if decision == "approved":
        logger.info("Admin approved content: content_id=%s", content_id)
        return {
            "admin_decision": "approved",
            "current_draft_id": content_id,
            "pipeline_status": "awaiting_approval",
        }

    if decision == "revision_requested":
        feedback = admin_response.get("feedback", "")
        logger.info("Admin requested revision: content_id=%s, feedback=%s", content_id, feedback)
        return {
            "admin_decision": "revision_requested",
            "admin_feedback": feedback,
            "current_draft_id": content_id,
        }

    # rejected
    reason = admin_response.get("reason", "")
    logger.info("Admin rejected content: content_id=%s, reason=%s", content_id, reason)
    await update_content_status(
        content_id, "rejected", rejection_reason=reason or "Rejected by admin"
    )
    return {
        "admin_decision": "rejected",
        "admin_feedback": reason,
        "pipeline_status": "failed",
        "current_draft_id": content_id,
    }
