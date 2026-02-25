---
phase: 08-admin-dashboard-ui
plan: 02
subsystem: admin-frontend
tags: [nextjs, react, tanstack-table, shadcn, tailwind, magazine-preview]
dependency-graph:
  requires: ["08-01"]
  provides: ["content-list-page", "content-detail-page", "block-renderer", "magazine-preview"]
  affects: ["08-03"]
tech-stack:
  added: []
  patterns: ["server-component-data-fetching", "url-driven-filtering", "block-renderer-dispatch", "defensive-rendering"]
key-files:
  created:
    - admin/src/app/contents/page.tsx
    - admin/src/app/contents/[id]/page.tsx
    - admin/src/components/content-table.tsx
    - admin/src/components/content-status-badge.tsx
    - admin/src/components/block-renderer.tsx
    - admin/src/components/json-panel.tsx
    - admin/src/components/blocks/hero-block.tsx
    - admin/src/components/blocks/headline-block.tsx
    - admin/src/components/blocks/body-text-block.tsx
    - admin/src/components/blocks/image-gallery-block.tsx
    - admin/src/components/blocks/pull-quote-block.tsx
    - admin/src/components/blocks/product-showcase-block.tsx
    - admin/src/components/blocks/celeb-feature-block.tsx
    - admin/src/components/blocks/divider-block.tsx
    - admin/src/components/blocks/hashtag-bar-block.tsx
    - admin/src/components/blocks/credits-block.tsx
  modified: []
key-decisions:
  - id: block-dispatch-pattern
    decision: "Record<string, ComponentType> map for block type dispatch with unknown-type fallback"
    reason: "Simple, extensible, graceful degradation for AI-generated content"
  - id: url-driven-state
    decision: "Tab filters and pagination use URL searchParams, not client state"
    reason: "Shareable URLs, server-side filtering, browser back/forward works"
  - id: defensive-rendering
    decision: "All block components use optional chaining and fallback values"
    reason: "AI-generated layout JSON may have missing/unexpected fields"
duration: ~3m
completed: 2026-02-25
---

# Phase 08 Plan 02: Content List and Detail Pages Summary

**One-liner:** Content list with tanstack-table/tabs/pagination + detail page with 10 magazine-style block preview components and collapsible JSON panel

## Performance Metrics

- Duration: ~3 minutes
- Tasks: 2/2 completed
- Build: passes with 0 TypeScript errors

## Accomplishments

1. **Content list page** (`/contents`) - Server Component fetching from BFF proxy with URL-driven status filtering (All/Pending/Approved/Rejected tabs) and pagination (20 items/page, Previous/Next navigation)

2. **Content table** - tanstack/react-table with sortable Title and Created columns, status badges with color-coded variants (amber=pending, green=approved, red=rejected), clickable rows navigating to detail page

3. **10 block preview components** - Magazine-style rendering of all LayoutBlock types: hero (16:9 overlay), headline (serif h1/h2/h3), body_text (paragraphs), image_gallery (grid/carousel/masonry), pull_quote (bordered italic), product_showcase (card grid), celeb_feature (circular avatars), divider (line/space/ornament), hashtag_bar (pill tags), credits (role/name pairs)

4. **Block renderer** - Dispatcher mapping block type string to React component with orange dashed warning for unknown types (never crashes)

5. **Content detail page** (`/contents/[id]`) - Full metadata display (title, status badge, keyword, dates, review summary, rejection reason, admin feedback) + magazine preview + collapsible raw JSON panel

## Task Commits

| Task | Name | Commit | Key Files |
|------|------|--------|-----------|
| 1 | Content list page with table, tabs, and pagination | e524f61 | contents/page.tsx, content-table.tsx, content-status-badge.tsx |
| 2 | Block renderer components and detail page | d65d20f | 10 block components, block-renderer.tsx, json-panel.tsx, contents/[id]/page.tsx |

## Files Created

- `admin/src/app/contents/page.tsx` - Server Component, content list with error handling
- `admin/src/app/contents/[id]/page.tsx` - Server Component, content detail with block preview
- `admin/src/components/content-table.tsx` - Client Component, tanstack table with tabs + pagination
- `admin/src/components/content-status-badge.tsx` - Status to colored Badge mapping
- `admin/src/components/block-renderer.tsx` - Block type dispatcher with unknown-type fallback
- `admin/src/components/json-panel.tsx` - Client Component, collapsible JSON viewer
- `admin/src/components/blocks/*.tsx` - 10 block preview components

## Decisions Made

| Decision | Rationale |
|----------|-----------|
| URL searchParams for filtering/pagination | Shareable URLs, SSR-compatible, browser history works |
| Record<string, ComponentType> block dispatch | Simple extensible mapping; unknown types show warning |
| Optional chaining + fallbacks in all blocks | AI-generated JSON may have missing fields; never crash |
| force-dynamic on server pages | Prevents build-time pre-rendering (fetch to own server fails at build) |
| Colored placeholder boxes for images | Clear visual indication of image placement without real assets |

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## Next Phase Readiness

Plan 08-03 (approve/reject actions) can proceed. The detail page is ready to receive action buttons - it currently renders read-only preview with all metadata sections (review_summary, rejection_reason, admin_feedback) already displayed. The BFF proxy approve/reject routes from 08-01 are ready to be called.
