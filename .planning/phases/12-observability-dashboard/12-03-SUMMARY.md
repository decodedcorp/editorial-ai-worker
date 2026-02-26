---
phase: 12-observability-dashboard
plan: 03
subsystem: ui, api
tags: [pipeline-status, step-dots, bff-enrichment, list-page, observability]

# Dependency graph
requires:
  - phase: 12-01
    provides: BFF proxy, TypeScript log types, cost/duration utilities
provides:
  - PipelineStatusIndicator component with step dots + badge + summary metrics
  - BFF content list enrichment merging log summaries server-side
  - ContentItemWithSummary type for enriched list items
affects: []

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Server-side N+1 resolution via Promise.all in BFF list proxy"
    - "Step dots + badge pattern for compact pipeline status in table rows"

key-files:
  created:
    - admin/src/components/pipeline-status-indicator.tsx
  modified:
    - admin/src/app/api/contents/route.ts
    - admin/src/lib/types.ts
    - admin/src/components/content-table.tsx
    - admin/src/app/contents/page.tsx

key-decisions:
  - "BFF enriches list items server-side via parallel log fetches (single HTTP from browser)"
  - "Retry count derived from editorial node occurrence count minus one"
  - "All 5 dots filled for terminal statuses; mid-pipeline stages reserved for detail page"

# Metrics
duration: 2min
completed: 2026-02-26
---

# Phase 12 Plan 03: List Page Pipeline Status Summary

**Pipeline status indicator with step dots, badges, and summary metrics (duration, cost, retries) in content list table, backed by BFF server-side log enrichment**

## Performance

- **Duration:** 2 min
- **Started:** 2026-02-26T08:53:11Z
- **Completed:** 2026-02-26T08:55:29Z
- **Tasks:** 3
- **Files modified:** 5

## Accomplishments
- BFF content list proxy enriches each item with pipeline_summary (total_duration_ms, estimated_cost_usd, retry_count) via parallel server-side log fetches
- PipelineStatusIndicator component renders 5 step dots + text badge + optional summary metrics row
- Content table now has Pipeline column between Status and Keyword columns
- Color-coded visual treatment: amber (pending/awaiting approval), green (approved/published), red (rejected)
- Graceful degradation: items without logs show dots + badge only (no metrics row)

## Task Commits

Each task was committed atomically:

1. **Task 1: BFF content list enrichment + ContentItemWithSummary type** - `1777654` (feat)
2. **Task 2: PipelineStatusIndicator component** - `ccd4790` (feat)
3. **Task 3: Content table Pipeline column + list page wiring** - `1e5b7a9` (feat)

## Files Created/Modified
- `admin/src/lib/types.ts` - Added PipelineSummaryFields, ContentItemWithSummary, ContentListWithSummaryResponse
- `admin/src/app/api/contents/route.ts` - BFF list proxy now fetches log summaries in parallel and merges into response
- `admin/src/components/pipeline-status-indicator.tsx` - New component: step dots + badge + summary metrics
- `admin/src/components/content-table.tsx` - Added Pipeline column using ContentItemWithSummary type
- `admin/src/app/contents/page.tsx` - Updated to use ContentListWithSummaryResponse type

## Decisions Made
- BFF enriches list items server-side via Promise.all parallel log fetches (no N+1 from browser)
- Retry count derived from counting "editorial" node appearances minus one (each retry re-runs editorial)
- All 5 dots filled for all terminal statuses; mid-pipeline stages are detail-page-only (no WebSocket/polling on list)
- Cost estimation reuses same estimateCost utility from 12-01 for consistency with detail page

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed TypeScript type mismatch in demo mode**
- **Found during:** Task 1
- **Issue:** Plan used `Record<string, unknown>` for demo item map callback, but `getDemoItems` returns `ContentItem[]` which is not assignable to `Record<string, unknown>`
- **Fix:** Changed type annotation to `ContentItem` and added explicit import
- **Files modified:** admin/src/app/api/contents/route.ts
- **Commit:** 1777654

## Issues Encountered

None

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- List page pipeline status fully functional
- All 12-03 artifacts ready; 12-02 (Pipeline tab) executing in parallel
- Phase 12 completion depends on 12-02 finishing

---
*Phase: 12-observability-dashboard*
*Completed: 2026-02-26*
