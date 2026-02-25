"""Stub node functions for the editorial pipeline graph.

Each stub returns minimal state updates. They will be replaced with real
implementations in subsequent phases.
"""

from __future__ import annotations

from editorial_ai.state import EditorialPipelineState


def stub_curation(state: EditorialPipelineState) -> dict:
    """Stub: Phase 2에서 구현. 키워드 기반 큐레이션."""
    return {
        "pipeline_status": "sourcing",
        "curated_topics": [],
    }


def stub_source(state: EditorialPipelineState) -> dict:
    """Stub: Phase 2에서 구현. 외부 소스 수집 및 컨텍스트 강화."""
    return {
        "pipeline_status": "drafting",
        "enriched_contexts": [],
    }


def stub_editorial(state: EditorialPipelineState) -> dict:
    """Stub: Phase 3에서 구현. 에디토리얼 콘텐츠 생성."""
    return {
        "pipeline_status": "reviewing",
        "current_draft_id": None,
    }


def stub_review(state: EditorialPipelineState) -> dict:
    """Stub review node. Real implementation in nodes/review.py (Phase 6)."""
    return {
        "pipeline_status": "awaiting_approval",
        "review_result": {"passed": True},
    }


def stub_admin_gate(state: EditorialPipelineState) -> dict:
    """Stub kept for backward compatibility. Real implementation in nodes/admin_gate.py."""
    return {
        "pipeline_status": "published",
        "admin_decision": "approved",
    }


def stub_enrich(state: EditorialPipelineState) -> dict:
    """Stub: Phase 5에서 구현. DB 데이터 enrichment."""
    return {}


def stub_publish(state: EditorialPipelineState) -> dict:
    """Stub kept for backward compatibility. Real implementation in nodes/publish.py."""
    return {
        "pipeline_status": "published",
    }
