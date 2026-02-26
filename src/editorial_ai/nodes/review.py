"""Review node for the editorial pipeline graph.

Thin wrapper around ReviewService: reads current_draft and curated_topics
from state, runs hybrid evaluation, writes review results back to state.
"""

from __future__ import annotations

import json
import logging

from editorial_ai.caching import get_cache_manager
from editorial_ai.routing import get_model_router
from editorial_ai.rubrics import classify_content_type, get_rubric
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

    # Classify content type and get adaptive rubric
    curation_input = state.get("curation_input") or {}
    seed_keyword = curation_input.get("keyword", "")
    content_type = classify_content_type(seed_keyword, curated_topics)
    rubric_config = get_rubric(content_type)
    logger.info(
        "Review using %s rubric for keyword=%s", content_type.value, seed_keyword
    )

    # Cache curated_topics on retry -- same topics, different draft
    revision_count = state.get("revision_count", 0)
    cache_name = None
    if revision_count > 0 and curated_topics:
        topics_json = json.dumps(curated_topics, ensure_ascii=False)
        thread_id = state.get("thread_id") or "unknown"
        cache_key = f"review-topics-{thread_id}"
        try:
            model = get_model_router().resolve(
                "review", revision_count=revision_count
            ).model
            cache_mgr = get_cache_manager()
            cache_name = await cache_mgr.get_or_create(
                cache_key=cache_key,
                model=model,
                contents=topics_json,
                system_instruction="다음은 큐레이션된 토픽 데이터입니다. 에디토리얼 초안을 이 데이터와 대조하여 평가하세요.",
            )
        except Exception:
            logger.warning("Failed to create review cache, proceeding without", exc_info=True)

    try:
        service = ReviewService(get_genai_client())
        result = await service.evaluate(
            current_draft,
            curated_topics,
            rubric_config=rubric_config,
            revision_count=revision_count,
            cache_name=cache_name,
        )
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
