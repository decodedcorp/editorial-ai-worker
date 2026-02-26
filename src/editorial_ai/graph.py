"""Editorial pipeline graph definition.

Defines the StateGraph topology with real node implementations and conditional edges.
The graph follows: curation -> design_spec -> source -> editorial -> enrich -> review -> admin_gate -> publish
with conditional routing after review (retry/fail) and admin_gate (revision/reject).
Review node performs LLM-as-a-Judge evaluation (Phase 6).
Admin gate uses LangGraph interrupt() for human-in-the-loop approval (Phase 7).
Publish node finalizes approved content in Supabase (Phase 7).
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph

from editorial_ai.observability import node_wrapper
from editorial_ai.nodes.admin_gate import admin_gate
from editorial_ai.nodes.curation import curation_node
from editorial_ai.nodes.design_spec import design_spec_node
from editorial_ai.nodes.editorial import editorial_node
from editorial_ai.nodes.enrich import enrich_editorial_node  # noqa: F401 — kept for node_overrides
from editorial_ai.nodes.enrich_from_posts import enrich_from_posts_node
from editorial_ai.nodes.publish import publish_node
from editorial_ai.nodes.review import review_node
from editorial_ai.nodes.source import source_node
from editorial_ai.nodes.stubs import (
    stub_admin_gate,  # noqa: F401 — kept for backward compat (tests use via node_overrides)
    stub_curation,  # noqa: F401 — kept for backward compat (tests use via node_overrides)
    stub_editorial,  # noqa: F401 — kept for backward compat (tests use via node_overrides)
    stub_enrich,  # noqa: F401 — kept for backward compat (tests use via node_overrides)
    stub_publish,  # noqa: F401 — kept for backward compat (tests use via node_overrides)
    stub_review,  # noqa: F401 — kept for backward compat (tests use via node_overrides)
    stub_design_spec,  # noqa: F401 — kept for backward compat
    stub_source,  # noqa: F401 — kept for backward compat
)
from editorial_ai.state import EditorialPipelineState


def route_after_review(state: EditorialPipelineState) -> str:
    """Route after review node based on review result and revision count."""
    review_result = state.get("review_result") or {}
    if review_result.get("passed"):
        return "admin_gate"
    if state.get("revision_count", 0) >= 3:
        return END
    return "editorial"


def route_after_admin(state: EditorialPipelineState) -> str:
    """Route after admin gate based on admin decision."""
    decision = state.get("admin_decision")
    if decision == "approved":
        return "publish"
    if decision == "revision_requested":
        return "editorial"
    return END  # rejected or unknown


def build_graph(
    *,
    node_overrides: dict[str, Callable[..., Any]] | None = None,
    checkpointer: BaseCheckpointSaver | None = None,
) -> CompiledStateGraph:
    """Build and compile the editorial pipeline graph.

    Args:
        node_overrides: Optional dict mapping node names to replacement functions.
            Useful for testing with mock nodes.
        checkpointer: Optional checkpoint saver for state persistence.
            When provided, graph state is saved after each node execution.

    Returns:
        Compiled StateGraph ready for invocation.
    """
    nodes: dict[str, Callable[..., Any]] = {
        "curation": curation_node,
        "design_spec": design_spec_node,
        "source": source_node,
        "editorial": editorial_node,
        "enrich": enrich_from_posts_node,  # Posts-based enrichment
        "review": review_node,
        "admin_gate": admin_gate,
        "publish": publish_node,
    }
    if node_overrides:
        nodes.update(node_overrides)

    # Wrap all nodes with observability instrumentation
    for name in list(nodes.keys()):
        nodes[name] = node_wrapper(name)(nodes[name])

    builder = StateGraph(EditorialPipelineState)

    for name, fn in nodes.items():
        builder.add_node(name, fn)

    # Sequential edges
    builder.add_edge(START, "curation")
    builder.add_edge("curation", "design_spec")
    builder.add_edge("design_spec", "source")
    builder.add_edge("source", "editorial")
    builder.add_edge("editorial", "enrich")
    builder.add_edge("enrich", "review")

    # Conditional edges
    builder.add_conditional_edges(
        "review", route_after_review, ["admin_gate", "editorial", END]
    )
    builder.add_conditional_edges(
        "admin_gate", route_after_admin, ["publish", "editorial", END]
    )

    # Terminal edge
    builder.add_edge("publish", END)

    return builder.compile(checkpointer=checkpointer)


# Default compiled graph for production use
graph = build_graph()
