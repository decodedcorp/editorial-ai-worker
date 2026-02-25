"""Tests for checkpointer integration using MemorySaver (no external DB)."""

from __future__ import annotations

import json

import pytest
from langgraph.checkpoint.memory import MemorySaver

from editorial_ai.graph import build_graph


def _minimal_input() -> dict:
    """Return minimal input state for graph invocation."""
    return {"curation_input": {"keyword": "spring fashion"}}


def test_build_graph_with_checkpointer():
    """Graph compiles successfully with a checkpointer."""
    checkpointer = MemorySaver()
    graph = build_graph(checkpointer=checkpointer)
    assert graph is not None


@pytest.mark.asyncio
async def test_state_persists_with_checkpointer():
    """Verify that graph state is saved and retrievable via thread_id."""
    checkpointer = MemorySaver()
    graph = build_graph(checkpointer=checkpointer)

    config = {"configurable": {"thread_id": "test-persist-001"}}

    await graph.ainvoke(_minimal_input(), config=config)

    saved = await graph.aget_state(config)
    assert saved is not None
    assert saved.values.get("pipeline_status") is not None


@pytest.mark.asyncio
async def test_state_recoverable_on_resume():
    """Simulate process restart: build new graph, same thread_id, state restored."""
    checkpointer = MemorySaver()

    # First invocation
    graph1 = build_graph(checkpointer=checkpointer)
    config = {"configurable": {"thread_id": "test-resume-001"}}
    await graph1.ainvoke(
        {"curation_input": {"keyword": "summer trends"}},
        config=config,
    )

    # "Restart": build new graph with SAME checkpointer
    graph2 = build_graph(checkpointer=checkpointer)
    saved = await graph2.aget_state(config)
    assert saved is not None
    assert saved.values.get("curation_input") == {"keyword": "summer trends"}


@pytest.mark.asyncio
async def test_lean_state_no_fat_payloads():
    """Verify checkpointed state contains only lean data (IDs, status, small dicts).

    The lean state principle: IDs and references only, not full payloads.
    This test ensures the state schema enforces this by checking that
    all values in the checkpointed state are reasonably small.
    """
    checkpointer = MemorySaver()
    graph = build_graph(checkpointer=checkpointer)
    config = {"configurable": {"thread_id": "test-lean-001"}}

    await graph.ainvoke(_minimal_input(), config=config)

    saved = await graph.aget_state(config)
    state = saved.values

    # Serialize state to JSON and check total size
    state_json = json.dumps(state, default=str)
    # Lean state should be well under 10KB even with all fields populated
    assert len(state_json) < 10_000, (
        f"State too large ({len(state_json)} bytes). "
        "Check for fat payloads violating lean state principle."
    )


@pytest.mark.asyncio
async def test_thread_isolation():
    """Different thread_ids have independent state."""
    checkpointer = MemorySaver()
    graph = build_graph(checkpointer=checkpointer)

    config_a = {"configurable": {"thread_id": "thread-a"}}
    config_b = {"configurable": {"thread_id": "thread-b"}}

    await graph.ainvoke(
        {"curation_input": {"keyword": "alpha"}}, config=config_a
    )
    await graph.ainvoke(
        {"curation_input": {"keyword": "beta"}}, config=config_b
    )

    state_a = await graph.aget_state(config_a)
    state_b = await graph.aget_state(config_b)

    assert state_a.values["curation_input"]["keyword"] == "alpha"
    assert state_b.values["curation_input"]["keyword"] == "beta"
