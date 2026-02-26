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

    # Design Spec (generated from curated keyword, consumed by editorial node)
    design_spec: dict | None

    # Source Phase
    enriched_contexts: list[dict]

    # Editorial Phase
    current_draft: dict | None  # MagazineLayout JSON (temporary; Phase 7 moves to Supabase)
    current_draft_id: str | None
    tool_calls_log: Annotated[list[dict], operator.add]

    # Review Phase
    review_result: dict | None
    revision_count: int
    feedback_history: Annotated[list[dict], operator.add]

    # Thread tracking (set by API trigger, used by admin_gate for Supabase upsert)
    thread_id: str | None

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
