"""Editorial pipeline shared state definition.

Lean state principle: store IDs and references only, not full payloads.
"""

from __future__ import annotations

import operator
from typing import Annotated, Literal, TypedDict


class EditorialPipelineState(TypedDict):
    """파이프라인 공유 상태. Lean 원칙: ID/참조만, 페이로드는 외부 저장."""

    # Curation Phase
    curation_input: dict
    curated_topics: list[dict]

    # Source Phase
    enriched_contexts: list[dict]

    # Editorial Phase
    current_draft_id: str | None
    tool_calls_log: Annotated[list[dict], operator.add]

    # Review Phase
    review_result: dict | None
    revision_count: int
    feedback_history: Annotated[list[dict], operator.add]

    # Admin Gate
    admin_decision: Literal["approved", "rejected", "revision_requested"] | None
    admin_feedback: str | None

    # Pipeline Meta
    pipeline_status: Literal[
        "curating",
        "sourcing",
        "drafting",
        "reviewing",
        "awaiting_approval",
        "published",
        "failed",
    ]
    error_log: Annotated[list[str], operator.add]
