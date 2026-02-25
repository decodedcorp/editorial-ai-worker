"""Review node for the editorial pipeline graph.

Thin wrapper around ReviewService: reads current_draft and curated_topics
from state, runs hybrid evaluation, writes review results back to state.
"""

from __future__ import annotations

import logging

from editorial_ai.services.curation_service import get_genai_client
from editorial_ai.services.review_service import ReviewService
from editorial_ai.state import EditorialPipelineState

logger = logging.getLogger(__name__)

MAX_REVISIONS = 3


async def review_node(state: EditorialPipelineState) -> dict:
    """LangGraph node: evaluate editorial draft quality.

    Reads current_draft and curated_topics from state, calls ReviewService
    for hybrid evaluation (Pydantic format + LLM semantic), writes review
    results back to state.

    On pass: sets pipeline_status = "awaiting_approval"
    On fail: increments revision_count, appends to feedback_history
    On escalation (revision_count >= MAX_REVISIONS and still failing):
        sets pipeline_status = "failed", appends to error_log
    """
    current_draft = state.get("current_draft")
    if not current_draft:
        revision_count = state.get("revision_count", 0) + 1
        return {
            "review_result": {"passed": False},
            "revision_count": revision_count,
            "feedback_history": [
                {"criteria": [], "summary": "No draft to review"}
            ],
            "error_log": ["Review skipped: no current_draft in state"],
        }

    curated_topics = state.get("curated_topics") or []

    try:
        service = ReviewService(get_genai_client())
        result = await service.evaluate(current_draft, curated_topics)
    except Exception as e:  # noqa: BLE001
        logger.exception("Review node failed")
        return {
            "review_result": {"passed": False},
            "revision_count": state.get("revision_count", 0) + 1,
            "feedback_history": [
                {"criteria": [], "summary": f"Review error: {e!s}"}
            ],
            "error_log": [f"Review failed: {type(e).__name__}: {e!s}"],
        }

    result_dict = result.model_dump()
    update: dict = {"review_result": result_dict}

    if result.passed:
        update["pipeline_status"] = "awaiting_approval"
    else:
        new_revision_count = state.get("revision_count", 0) + 1
        update["revision_count"] = new_revision_count
        update["feedback_history"] = [result_dict]  # appended via operator.add

        # Escalation: max retries reached and still failing
        if new_revision_count >= MAX_REVISIONS:
            update["pipeline_status"] = "failed"
            update["error_log"] = [
                f"Escalation: review failed after {new_revision_count} attempts. "
                f"Last failure: {result.summary}"
            ]

    return update
