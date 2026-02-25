"""Integration tests for admin_gate interrupt/resume flow with MemorySaver.

Tests the full HITL loop: graph pauses at admin_gate interrupt, then resumes
with approve/reject/revision decisions via Command(resume=...).
"""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
from langgraph.checkpoint.memory import MemorySaver
from langgraph.types import Command

from editorial_ai.graph import build_graph
from editorial_ai.nodes.stubs import stub_enrich


def _stub_overrides_except_admin_gate_and_publish() -> dict:
    """Return node_overrides that stub everything except admin_gate and publish.

    Stubs produce minimal state that admin_gate expects:
    - curated_topics, curation_input for keyword extraction
    - current_draft with title for content save
    - review_result with passed=True and summary for admin snapshot
    """

    def stub_curation_with_data(state: dict) -> dict:
        return {
            "pipeline_status": "sourcing",
            "curated_topics": [{"title": "Test Topic", "keywords": ["test"]}],
        }

    def stub_source_with_data(state: dict) -> dict:
        return {
            "pipeline_status": "drafting",
            "enriched_contexts": [{"source": "test", "content": "test context"}],
        }

    def stub_editorial_with_draft(state: dict) -> dict:
        return {
            "pipeline_status": "reviewing",
            "current_draft": {"title": "Test Article", "keyword": "test"},
            "current_draft_id": None,
        }

    def stub_review_passed(state: dict) -> dict:
        return {
            "pipeline_status": "awaiting_approval",
            "review_result": {"passed": True, "summary": "All checks passed"},
        }

    return {
        "curation": stub_curation_with_data,
        "source": stub_source_with_data,
        "editorial": stub_editorial_with_draft,
        "enrich": stub_enrich,
        "review": stub_review_passed,
    }


def _initial_state() -> dict:
    """Return a clean initial state for graph invocation."""
    return {
        "curation_input": {"seed_keyword": "test-keyword", "week": "2026-W08"},
        "curated_topics": [],
        "enriched_contexts": [],
        "current_draft": None,
        "current_draft_id": None,
        "tool_calls_log": [],
        "review_result": None,
        "revision_count": 0,
        "feedback_history": [],
        "admin_decision": None,
        "admin_feedback": None,
        "pipeline_status": "curating",
        "error_log": [],
    }


@pytest.mark.asyncio
@patch(
    "editorial_ai.nodes.admin_gate.save_pending_content",
    new_callable=AsyncMock,
    return_value={"id": "content-123", "status": "pending"},
)
@patch(
    "editorial_ai.nodes.admin_gate.update_content_status",
    new_callable=AsyncMock,
    return_value={"id": "content-123", "status": "rejected"},
)
@patch(
    "editorial_ai.nodes.publish.update_content_status",
    new_callable=AsyncMock,
    return_value={"id": "content-123", "status": "published"},
)
async def test_admin_gate_pauses_at_interrupt(
    mock_publish_update,
    mock_gate_update,
    mock_save,
):
    """Graph pauses at admin_gate interrupt -- does not reach publish."""
    checkpointer = MemorySaver()
    graph = build_graph(
        node_overrides=_stub_overrides_except_admin_gate_and_publish(),
        checkpointer=checkpointer,
    )

    config = {"configurable": {"thread_id": "test-pause-1"}}
    result = await graph.ainvoke(_initial_state(), config=config)

    # Graph should pause at interrupt -- pipeline_status should be awaiting_approval
    # or the state before publish ran. Key: admin_decision should NOT be set yet
    # (interrupt pauses before returning from admin_gate).
    # When LangGraph hits interrupt(), ainvoke returns the state at that point.
    assert result.get("pipeline_status") != "published"
    assert result.get("admin_decision") is None

    # save_pending_content should have been called (content saved before interrupt)
    mock_save.assert_called_once()

    # publish should NOT have been called
    mock_publish_update.assert_not_called()


@pytest.mark.asyncio
@patch(
    "editorial_ai.nodes.admin_gate.save_pending_content",
    new_callable=AsyncMock,
    return_value={"id": "content-456", "status": "pending"},
)
@patch(
    "editorial_ai.nodes.admin_gate.update_content_status",
    new_callable=AsyncMock,
    return_value={"id": "content-456", "status": "rejected"},
)
@patch(
    "editorial_ai.nodes.publish.update_content_status",
    new_callable=AsyncMock,
    return_value={"id": "content-456", "status": "published"},
)
async def test_resume_with_approval_flows_to_publish(
    mock_publish_update,
    mock_gate_update,
    mock_save,
):
    """Resume with approved decision flows through publish node."""
    checkpointer = MemorySaver()
    graph = build_graph(
        node_overrides=_stub_overrides_except_admin_gate_and_publish(),
        checkpointer=checkpointer,
    )

    config = {"configurable": {"thread_id": "test-approve-1"}}

    # Phase 1: Run until interrupt
    await graph.ainvoke(_initial_state(), config=config)

    # Phase 2: Resume with approval
    result = await graph.ainvoke(
        Command(resume={"decision": "approved"}),
        config=config,
    )

    assert result["admin_decision"] == "approved"
    assert result["pipeline_status"] == "published"

    # publish_node should have called update_content_status
    mock_publish_update.assert_called_once()


@pytest.mark.asyncio
@patch(
    "editorial_ai.nodes.admin_gate.save_pending_content",
    new_callable=AsyncMock,
    return_value={"id": "content-789", "status": "pending"},
)
@patch(
    "editorial_ai.nodes.admin_gate.update_content_status",
    new_callable=AsyncMock,
    return_value={"id": "content-789", "status": "rejected"},
)
@patch(
    "editorial_ai.nodes.publish.update_content_status",
    new_callable=AsyncMock,
    return_value={"id": "content-789", "status": "published"},
)
async def test_resume_with_rejection_terminates(
    mock_publish_update,
    mock_gate_update,
    mock_save,
):
    """Resume with rejected decision terminates pipeline with failed status."""
    checkpointer = MemorySaver()
    graph = build_graph(
        node_overrides=_stub_overrides_except_admin_gate_and_publish(),
        checkpointer=checkpointer,
    )

    config = {"configurable": {"thread_id": "test-reject-1"}}

    # Phase 1: Run until interrupt
    await graph.ainvoke(_initial_state(), config=config)

    # Phase 2: Resume with rejection
    result = await graph.ainvoke(
        Command(resume={"decision": "rejected", "reason": "Low quality"}),
        config=config,
    )

    assert result["admin_decision"] == "rejected"
    assert result["pipeline_status"] == "failed"

    # admin_gate should have called update_content_status for rejection
    mock_gate_update.assert_called_once()

    # publish_node should NOT have been called
    mock_publish_update.assert_not_called()


@pytest.mark.asyncio
@patch(
    "editorial_ai.nodes.admin_gate.save_pending_content",
    new_callable=AsyncMock,
    return_value={"id": "content-rev-1", "status": "pending"},
)
@patch(
    "editorial_ai.nodes.admin_gate.update_content_status",
    new_callable=AsyncMock,
)
@patch(
    "editorial_ai.nodes.publish.update_content_status",
    new_callable=AsyncMock,
)
async def test_resume_with_revision_routes_to_editorial(
    mock_publish_update,
    mock_gate_update,
    mock_save,
):
    """Resume with revision_requested routes back to editorial node."""
    # Track editorial calls to detect re-entry
    editorial_call_count = 0

    def stub_editorial_tracking(state: dict) -> dict:
        nonlocal editorial_call_count
        editorial_call_count += 1
        return {
            "pipeline_status": "reviewing",
            "current_draft": {"title": f"Draft v{editorial_call_count}", "keyword": "test"},
            "current_draft_id": None,
        }

    overrides = _stub_overrides_except_admin_gate_and_publish()
    overrides["editorial"] = stub_editorial_tracking

    # admin_gate will be called twice: first time we request revision,
    # second time we approve. We need to handle the second interrupt too.
    checkpointer = MemorySaver()
    graph = build_graph(
        node_overrides=overrides,
        checkpointer=checkpointer,
    )

    config = {"configurable": {"thread_id": "test-revision-1"}}

    # Phase 1: Run until first interrupt
    await graph.ainvoke(_initial_state(), config=config)
    assert editorial_call_count == 1

    # Phase 2: Resume with revision -> editorial -> review -> admin_gate (interrupt again)
    await graph.ainvoke(
        Command(resume={"decision": "revision_requested", "feedback": "Add more detail"}),
        config=config,
    )

    # Editorial should have been called again
    assert editorial_call_count == 2

    # Phase 3: Resume with approval this time
    result = await graph.ainvoke(
        Command(resume={"decision": "approved"}),
        config=config,
    )

    assert result["admin_decision"] == "approved"
    assert result["pipeline_status"] == "published"
