---
phase: 12-observability-dashboard
plan: 01
subsystem: api, ui
tags: [bff-proxy, typescript, cost-estimation, observability, gemini-pricing]

# Dependency graph
requires:
  - phase: 10-observability-backend
    provides: FastAPI logs endpoint (GET /api/contents/{id}/logs)
provides:
  - BFF proxy route for pipeline logs API
  - TypeScript types for LogsResponse, NodeRunLog, PipelineRunSummary, TokenUsageItem
  - Cost estimation and formatting utilities with Gemini pricing
  - Duration and number formatting utilities
affects: [12-02 Pipeline tab component, 12-03 List page status indicator]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "BFF proxy pattern for logs API (same as existing content routes)"
    - "Model-keyed pricing lookup for cost estimation extensibility"

key-files:
  created:
    - admin/src/app/api/contents/[id]/logs/route.ts
    - admin/src/components/pipeline/cost-utils.ts
  modified:
    - admin/src/lib/types.ts

key-decisions:
  - "Gemini 2.5 Flash as default pricing model for unknown model names"
  - "Sub-cent costs displayed as ~$0.00xx with 4 decimal places"

patterns-established:
  - "Cost utility pattern: estimateCost -> formatCost for token-to-USD display"
  - "Duration utility pattern: formatDuration for ms-to-human-readable conversion"

# Metrics
duration: 2min
completed: 2026-02-26
---

# Phase 12 Plan 01: Data Foundation Summary

**BFF proxy route for logs API, TypeScript log types mirroring Python schemas, and Gemini-priced cost/duration utilities**

## Performance

- **Duration:** 2 min
- **Started:** 2026-02-26T08:48:13Z
- **Completed:** 2026-02-26T08:50:13Z
- **Tasks:** 2
- **Files modified:** 3

## Accomplishments
- BFF proxy route forwards GET /api/contents/{id}/logs to FastAPI backend with API key hiding
- TypeScript types for TokenUsageItem, NodeRunLog, PipelineRunSummary, LogsResponse mirroring Python schemas
- Cost estimation utility with Gemini 2.5 Flash pricing and model-keyed lookup for Phase 13 extensibility
- Duration formatting handling ms, seconds, and minutes ranges

## Task Commits

Each task was committed atomically:

1. **Task 1: BFF proxy route + TypeScript types** - `d1d9aa9` (feat)
2. **Task 2: Cost and duration utilities** - `77cc04d` (feat)

## Files Created/Modified
- `admin/src/app/api/contents/[id]/logs/route.ts` - BFF proxy route forwarding logs requests with API key
- `admin/src/lib/types.ts` - Added TokenUsageItem, NodeRunLog, PipelineRunSummary, LogsResponse interfaces
- `admin/src/components/pipeline/cost-utils.ts` - estimateCost, formatCost, formatDuration, formatNumber utilities

## Decisions Made
- Gemini 2.5 Flash as default fallback pricing for unknown model names (safe default for current pipeline)
- Sub-cent costs displayed as `~$0.00xx` with 4 decimal places for precision; normal costs at 2 decimal places
- include_io query parameter defaults to "true" when not specified (matches backend default)

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- All types and utilities ready for 12-02 (Pipeline tab component) and 12-03 (list page status indicator)
- BFF proxy route can be tested end-to-end once backend is running with content data

---
*Phase: 12-observability-dashboard*
*Completed: 2026-02-26*
