"""Tests for the editorial pipeline graph topology."""

from __future__ import annotations

from langgraph.graph.state import CompiledStateGraph

from editorial_ai.graph import build_graph, graph
from editorial_ai.nodes.stubs import stub_curation, stub_editorial


def _initial_state() -> dict:
    """Return a clean initial state for graph invocation."""
    return {
        "curation_input": {"week": "2026-W08"},
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


def test_graph_compiles():
    """Graph compiles into a CompiledStateGraph instance."""
    assert graph is not None
    assert isinstance(graph, CompiledStateGraph)


def test_graph_compiles_with_real_editorial_node():
    """build_graph() without overrides compiles with async editorial node."""
    compiled = build_graph()
    assert isinstance(compiled, CompiledStateGraph)
    assert "editorial" in compiled.nodes


def test_graph_happy_path():
    """Happy path: all stubs pass, pipeline reaches 'published'."""
    sync_graph = build_graph(node_overrides={"curation": stub_curation, "editorial": stub_editorial})
    result = sync_graph.invoke(_initial_state())
    assert result["pipeline_status"] == "published"
    assert result["admin_decision"] == "approved"
    assert result["review_result"] == {"passed": True}


def test_graph_review_fail_then_pass():
    """Review fails once, then passes on retry -> published."""
    call_count = 0

    def mock_review(state: dict) -> dict:
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            return {
                "pipeline_status": "reviewing",
                "review_result": {"passed": False},
                "revision_count": state.get("revision_count", 0) + 1,
            }
        return {
            "pipeline_status": "awaiting_approval",
            "review_result": {"passed": True},
        }

    test_graph = build_graph(node_overrides={"curation": stub_curation, "editorial": stub_editorial, "review": mock_review})
    result = test_graph.invoke(_initial_state())
    assert result["pipeline_status"] == "published"
    assert call_count == 2


def test_graph_max_retries():
    """When revision_count >= 3, graph terminates without publishing."""
    call_count = 0

    def mock_review_always_fail(state: dict) -> dict:
        nonlocal call_count
        call_count += 1
        return {
            "pipeline_status": "reviewing",
            "review_result": {"passed": False},
            "revision_count": state.get("revision_count", 0) + 1,
        }

    test_graph = build_graph(node_overrides={"curation": stub_curation, "editorial": stub_editorial, "review": mock_review_always_fail})
    result = test_graph.invoke(_initial_state())
    assert result["pipeline_status"] != "published"
    assert result["revision_count"] >= 3


def test_graph_admin_revision_requested():
    """Admin requests revision -> routes back to editorial."""
    call_count = {"admin": 0}

    def mock_admin_gate(state: dict) -> dict:
        call_count["admin"] += 1
        if call_count["admin"] == 1:
            return {
                "pipeline_status": "awaiting_approval",
                "admin_decision": "revision_requested",
                "admin_feedback": "Needs more detail",
            }
        return {
            "pipeline_status": "published",
            "admin_decision": "approved",
        }

    test_graph = build_graph(node_overrides={"curation": stub_curation, "editorial": stub_editorial, "admin_gate": mock_admin_gate})
    result = test_graph.invoke(_initial_state())
    assert result["pipeline_status"] == "published"
    assert call_count["admin"] == 2
