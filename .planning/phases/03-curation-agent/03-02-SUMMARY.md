---
phase: 03-curation-agent
plan: 02
subsystem: curation-node
tags: [langgraph, async-node, state-wiring, curation, error-handling]

requires:
  - 03-01 (CurationService with curate_seed)
  - 01-02 (build_graph with node_overrides)

provides:
  - Async curation_node wired into LangGraph pipeline as default
  - State I/O: reads curation_input, writes curated_topics + pipeline_status
  - Error wrapping: missing keyword and API failures handled gracefully

affects:
  - 04 (Source Agent — next node in pipeline after curation)
  - Any future graph integration tests must use ainvoke() or stub_curation override

tech-stack:
  added: []
  patterns:
    - "Async LangGraph node wrapping service layer"
    - "Thin node pattern: state I/O + error wrapping only, business logic in service"
    - "Sync graph tests use stub_curation via node_overrides for backward compat"

key-files:
  created:
    - src/editorial_ai/nodes/curation.py
    - tests/test_curation_node.py
  modified:
    - src/editorial_ai/graph.py
    - tests/test_graph.py

key-decisions:
  - id: async-node-default
    decision: "Real async curation_node as default in build_graph, stub kept for import compat"
    reason: "Production graph should use real implementation; tests override via node_overrides"
  - id: sync-test-compat
    decision: "Existing sync graph tests updated to pass stub_curation override instead of converting to async"
    reason: "Graph topology tests should remain fast and independent of curation implementation"

duration: 2m
completed: 2026-02-25
---

# Phase 03 Plan 02: Curation Node Wiring Summary

Async curation_node wired into LangGraph: reads curation_input keyword, calls CurationService.curate_seed(), writes curated_topics as list[dict] to state with sourcing/failed status transitions.

## What Was Done

### Task 1: Curation node and graph wiring
- Created `src/editorial_ai/nodes/curation.py` with async `curation_node` function
- Node reads `state["curation_input"]["keyword"]`, creates CurationService, calls `curate_seed()`
- On success: returns `pipeline_status="sourcing"` + `curated_topics` as `model_dump()` dicts
- On missing keyword: returns `pipeline_status="failed"` with descriptive error_log
- On exception: catches all errors, returns `pipeline_status="failed"` with exception info
- Updated `graph.py` to import and use `curation_node` as default for "curation" key
- Kept `stub_curation` import for backward compatibility

### Task 2: Curation node tests and graph test compatibility
- Created 8 tests in `tests/test_curation_node.py`:
  - `test_returns_sourcing_with_topics` — success path with 3 topics
  - `test_topics_are_dicts_with_expected_fields` — model_dump field verification
  - `test_empty_curation_input` — empty dict returns failed
  - `test_missing_curation_input` — missing key returns failed
  - `test_does_not_call_service` — no service call on missing keyword
  - `test_exception_returns_failed` — API error handling
  - `test_empty_topics_is_valid` — empty results return sourcing (not failed)
  - `test_graph_compilation_with_real_curation_node` — graph compiles with async node
- Updated `tests/test_graph.py`: all sync invoke tests now pass `stub_curation` override

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Existing graph tests failed with async curation node**
- **Found during:** Task 2
- **Issue:** Module-level `graph = build_graph()` now uses async curation_node, causing `graph.invoke()` in test_graph.py to raise TypeError ("No synchronous function provided")
- **Fix:** Updated all 4 sync graph tests to pass `node_overrides={"curation": stub_curation}` as planned option (a)
- **Files modified:** tests/test_graph.py
- **Commit:** 9488a98

## Verification Results

- All 8 curation node tests pass
- All 5 existing graph tests pass (no regression)
- Full test suite: 45 passed, 3 deselected
- Ruff lint: clean
- Import verification: curation_node and build_graph both importable

## Next Phase Readiness

Phase 3 complete. The curation node is the first real async node in the pipeline. Key considerations for next phases:
- Source agent (Phase 4) will follow the same thin-node pattern
- Graph integration tests that invoke the full pipeline must use `ainvoke()` or stub async nodes
- The `curated_topics` state field contains list[dict] from CuratedTopic.model_dump()
