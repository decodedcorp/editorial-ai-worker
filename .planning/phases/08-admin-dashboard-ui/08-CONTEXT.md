# Phase 8: Admin Dashboard UI - Context

**Gathered:** 2026-02-25
**Status:** Ready for planning

<domain>
## Phase Boundary

관리자가 웹 브라우저에서 콘텐츠를 프리뷰하고 승인/반려할 수 있는 대시보드. Phase 7 API를 호출하는 프론트엔드. 콘텐츠 생성/수정 기능은 범위 밖 — 읽기 + 상태 변경만.

</domain>

<decisions>
## Implementation Decisions

### Tech Stack
- Next.js 15 + App Router
- Tailwind CSS + shadcn/ui for components
- pnpm as package manager
- Subdirectory: `admin/` inside current repo (not separate repo)

### Layout Rendering
- High fidelity preview — render blocks as close to final output as possible (real typography, spacing, colors)
- Image placeholders: colored box with image type label (e.g., "Hero Image", "Product Photo")
- Collapsible raw JSON panel toggle for debugging
- Responsive preview — fills available space, adapts to browser width

### List & Navigation
- Table layout with columns: title, status, created date, keyword
- Tab filters at top: All | Pending | Approved | Rejected (with badge counts)
- Click row → navigate to `/admin/[id]` detail page (new page, not modal/panel)
- Simple pagination (Previous/Next) at bottom, 10-20 items per page

### Approve/Reject Flow
- Sticky top bar on detail page: ← Back + status badge + Approve/Reject buttons (always visible)
- Approve: single click, no confirmation dialog
- Reject: clicking Reject expands inline text area for rejection reason, then Cancel/Confirm Reject
- After action: stay on page, update status badge in-place, disable action buttons

### Claude's Discretion
- Exact color scheme and typography choices
- Loading states and skeleton design
- Error state handling (API failures, network errors)
- Table sorting implementation details
- Mobile responsiveness of the dashboard itself

</decisions>

<specifics>
## Specific Ideas

- Table layout inspired by standard admin patterns (sortable columns, clean rows)
- Sticky top bar pattern for action buttons — always accessible while scrolling preview
- Rejection reason is inline (not modal) — keeps context of the preview visible

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 08-admin-dashboard-ui*
*Context gathered: 2026-02-25*
