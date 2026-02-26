---
phase: 10-pipeline-observability-backend
plan: 02
subsystem: observability
tags: [node-wrapper, decorator, token-tracking, pipeline-instrumentation, langgraph]

requires:
  - phase: 10-pipeline-observability-backend (10-01)
    provides: NodeRunLog model, TokenUsage collector, JSONL storage
provides:
  - node_wrapper decorator for automatic node instrumentation
  - Token usage recording at all 10 LLM call sites
  - Graph-level node wrapping in build_graph
affects:
  - 10-03 (pipeline summary endpoint needs NodeRunLog data produced here)
  - 11-pipeline-observability-dashboard (reads JSONL logs this produces)

tech-stack:
  added: []
  patterns: [decorator factory for node instrumentation, fire-and-forget token recording at call sites]

key-files:
  created:
    - src/editorial_ai/observability/node_wrapper.py
  modified:
    - src/editorial_ai/observability/__init__.py
    - src/editorial_ai/services/curation_service.py
    - src/editorial_ai/services/editorial_service.py
    - src/editorial_ai/services/review_service.py
    - src/editorial_ai/services/enrich_service.py
    - src/editorial_ai/graph.py

key-decisions:
  - "10 LLM call sites instrumented (plan listed 8, enrich_service had 2 additional module-level functions)"
  - "Sync node wrapper converts to async for uniform LangGraph compatibility"
  - "BaseException catch for node errors to handle KeyboardInterrupt etc., re-raised after logging"

patterns-established:
  - "Token recording pattern: if hasattr(response, 'usage_metadata') and response.usage_metadata -> record_token_usage()"
  - "Node wrapping in build_graph: applied after node_overrides for test compatibility"

duration: 3min
completed: 2026-02-26
---

# Phase 10 Plan 02: Node Wrapper and Service Instrumentation Summary

**node_wrapper decorator auto-instruments all 7 pipeline nodes with timing/state/token capture; record_token_usage injected at all 10 LLM call sites across 4 service files**

## Performance

- **Duration:** ~3 min
- **Started:** 2026-02-26T04:18:20Z
- **Completed:** 2026-02-26T04:21:20Z
- **Tasks:** 2
- **Files modified:** 7

## Accomplishments
- Created node_wrapper decorator that captures timing, state snapshots, token usage, and error details for every pipeline node
- Injected record_token_usage at all 10 generate_content call sites across curation, editorial, review, and enrich services
- Wired node_wrapper into build_graph so all 7 nodes are automatically wrapped at graph compilation time
- All instrumentation is fire-and-forget: failures never interrupt pipeline execution

## Task Commits

Each task was committed atomically:

1. **Task 1: node_wrapper decorator** - `6049255` (feat)
2. **Task 2: Inject record_token_usage + wire graph** - `91958d1` (feat)

## Files Created/Modified
- `src/editorial_ai/observability/node_wrapper.py` - Decorator factory with async/sync support, timing, state capture, token harvest, error logging
- `src/editorial_ai/observability/__init__.py` - Added node_wrapper to public exports
- `src/editorial_ai/services/curation_service.py` - 3 record_token_usage injections (research_trend, expand_subtopics, extract_topic)
- `src/editorial_ai/services/editorial_service.py` - 4 record_token_usage injections (generate_content, generate_layout_image, parse_layout_image, repair_output)
- `src/editorial_ai/services/review_service.py` - 1 record_token_usage injection (evaluate_with_llm)
- `src/editorial_ai/services/enrich_service.py` - 2 record_token_usage injections (expand_keywords, regenerate_with_enrichment)
- `src/editorial_ai/graph.py` - node_wrapper applied to all nodes in build_graph

## Decisions Made
- Instrumented 10 LLM call sites instead of 8 (plan missed 2 enrich_service module-level functions)
- Used BaseException catch for node errors to properly handle KeyboardInterrupt and SystemExit
- Node wrapping applied after node_overrides so test stubs also get wrapped

## Deviations from Plan
None - plan executed exactly as written. The 2 additional enrich_service call sites were mentioned in the plan but not counted in the "8 call sites" number.

## Issues Encountered
None

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- All pipeline nodes now produce NodeRunLog entries when executed
- Token usage is collected from every LLM call via ContextVar
- Ready for 10-03: pipeline summary endpoint and API exposure

---
*Phase: 10-pipeline-observability-backend*
*Completed: 2026-02-26*
