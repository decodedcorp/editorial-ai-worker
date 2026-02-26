---
phase: 10-pipeline-observability-backend
plan: 03
subsystem: api
tags: [fastapi, pydantic, observability, logs, rest-api]

requires:
  - phase: 10-01
    provides: NodeRunLog, PipelineRunSummary models and JSONL storage
provides:
  - GET /api/contents/{content_id}/logs endpoint with per-node metrics and summary
  - Pydantic response schemas for observability log data
affects: [12-observability-dashboard]

tech-stack:
  added: []
  patterns:
    - "Separate router file per concern (logs.py alongside admin.py)"
    - "include_io query param for payload size control"

key-files:
  created:
    - src/editorial_ai/api/routes/logs.py
  modified:
    - src/editorial_ai/api/schemas.py
    - src/editorial_ai/api/app.py

key-decisions:
  - "Logs router registered before admin router at same /api/contents prefix"
  - "include_io defaults to true; false nullifies input_state/output_state"

patterns-established:
  - "Query param toggle for optional response fields (include_io pattern)"

duration: 1min
completed: 2026-02-26
---

# Phase 10 Plan 03: Logs API Endpoint Summary

**GET /api/contents/{content_id}/logs endpoint serving per-node execution metrics with aggregated pipeline summary and optional IO snapshots**

## Performance

- **Duration:** 1 min
- **Started:** 2026-02-26T04:18:58Z
- **Completed:** 2026-02-26T04:20:05Z
- **Tasks:** 2
- **Files modified:** 3

## Accomplishments
- Pydantic response schemas (TokenUsageResponse, NodeRunLogResponse, PipelineRunSummaryResponse, LogsResponse)
- Logs endpoint resolving content_id to thread_id and serving chronological node logs
- include_io query param to control IO state inclusion in responses
- Empty logs return 200 with empty runs array and null summary

## Task Commits

Each task was committed atomically:

1. **Task 1: Logs API response schemas** - `0e45cae` (feat)
2. **Task 2: Logs route + app registration** - `7d2e9c4` (feat)

## Files Created/Modified
- `src/editorial_ai/api/schemas.py` - Added TokenUsageResponse, NodeRunLogResponse, PipelineRunSummaryResponse, LogsResponse
- `src/editorial_ai/api/routes/logs.py` - GET /{content_id}/logs endpoint with content lookup, log reading, sorting, summary aggregation
- `src/editorial_ai/api/app.py` - Registered logs router at /api/contents prefix

## Decisions Made
- Logs router registered as separate file (not added to admin.py) for clean separation of concerns
- Router placed before admin router to ensure /{content_id}/logs matches before /{content_id}
- include_io defaults to true; when false, sets input_state and output_state to None rather than excluding fields

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Logs endpoint ready for Phase 12 (Observability Dashboard) to consume
- Endpoint tested for import/registration; full integration test requires running pipeline with observability wrapper (10-02)

---
*Phase: 10-pipeline-observability-backend*
*Completed: 2026-02-26*
