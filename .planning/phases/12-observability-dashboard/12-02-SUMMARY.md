---
phase: 12-observability-dashboard
plan: 02
subsystem: ui
tags: [gantt-chart, timeline, pipeline-visualization, cost-estimation, react, observability]

# Dependency graph
requires:
  - phase: 12-01
    provides: BFF proxy route, TypeScript log types, cost/duration utilities
  - phase: 11-04
    provides: ContentTabs component, detail page layout
provides:
  - Gantt-style pipeline timeline visualization (PipelineTab)
  - Per-node cost/token detail panels (NodeDetailPanel)
  - Cost summary card with duration, tokens, cost, node count (CostSummaryCard)
  - Pipeline tab integrated into content detail page
affects: [12-03 list page status indicator]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Round grouping algorithm for retry visualization"
    - "Lazy IO loading pattern (fetch with include_io=true on demand)"
    - "Parallel server-side fetch (content + logs via Promise.all)"

key-files:
  created:
    - admin/src/components/pipeline/pipeline-tab.tsx
    - admin/src/components/pipeline/timeline-bar.tsx
    - admin/src/components/pipeline/node-detail-panel.tsx
    - admin/src/components/pipeline/cost-summary-card.tsx
  modified:
    - admin/src/components/content-tabs.tsx
    - admin/src/app/contents/[id]/page.tsx

key-decisions:
  - "Round grouping by detecting repeated node_name (editorial node marks new round)"
  - "IO data lazy-loaded on demand via separate fetch with include_io=true"
  - "Parallel fetch of content + logs on detail page with graceful fallback for logs failure"

patterns-established:
  - "Gantt bar width: Math.max((duration/total)*100, 1)% for minimum clickability"
  - "Node selection toggle: click to expand, click again to collapse"
  - "Round divider pattern: horizontal line + centered label for retry visualization"

# Metrics
duration: 3min
completed: 2026-02-26
---

# Phase 12 Plan 02: Pipeline Tab Summary

**Gantt-style pipeline timeline with per-node token/cost drill-down, round grouping for retries, and lazy IO loading**

## Performance

- **Duration:** 3 min
- **Started:** 2026-02-26T08:52:00Z
- **Completed:** 2026-02-26T08:55:00Z
- **Tasks:** 2
- **Files modified:** 6

## Accomplishments
- Gantt-style horizontal bar chart with proportional duration bars, color-coded by status
- Expandable node detail panel showing token breakdown, LLM call count, per-model cost, and error details
- Cost summary card with 4-metric grid (duration, tokens, cost, node count)
- Review retry rounds visually separated with "Round N" dividers
- IO data lazy-loaded on first node expand to avoid heavy initial page load
- Content + logs fetched in parallel on detail page with graceful logs failure fallback

## Task Commits

Each task was committed atomically:

1. **Task 1: Pipeline components (CostSummaryCard + TimelineBar + NodeDetailPanel)** - `035b3a4` (feat)
2. **Task 2: PipelineTab container + ContentTabs integration + detail page wiring** - `40b72e2` (feat)

## Files Created/Modified
- `admin/src/components/pipeline/cost-summary-card.tsx` - 4-metric summary card (duration, tokens, cost, nodes)
- `admin/src/components/pipeline/timeline-bar.tsx` - Single Gantt bar with proportional width and error coloring
- `admin/src/components/pipeline/node-detail-panel.tsx` - Expandable detail with token breakdown, errors, IO data
- `admin/src/components/pipeline/pipeline-tab.tsx` - Main container with round grouping, timeline, detail panel, IO lazy loading
- `admin/src/components/content-tabs.tsx` - Added Pipeline tab alongside Magazine and JSON
- `admin/src/app/contents/[id]/page.tsx` - Parallel fetch of content + logs, passes logs to ContentTabs

## Decisions Made
- Round grouping detects repeated node_name to start new round (editorial node appearing twice = new retry round)
- IO data lazy-loaded via separate API call with include_io=true, triggered by user clicking "Load IO data"
- Escalation banner shown when last review node error contains "escalat" (case-insensitive)
- Minimum bar width of 1% ensures fast nodes remain clickable in the Gantt chart

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- All pipeline visualization components complete for content detail page
- Ready for 12-03 (list page status indicators) which is the final plan in Phase 12

---
*Phase: 12-observability-dashboard*
*Completed: 2026-02-26*
