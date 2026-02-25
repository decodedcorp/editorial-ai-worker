---
phase: 08-admin-dashboard-ui
plan: 01
subsystem: admin-dashboard
tags: [next.js, shadcn-ui, typescript, bff-proxy, tailwind-v4]
requires: [07-02]
provides: [admin-project-skeleton, typescript-types, bff-proxy-routes, api-client]
affects: [08-02, 08-03]
tech-stack:
  added: [next.js-15, shadcn-ui, tanstack-react-table, date-fns, tailwind-v4, geist-font]
  patterns: [bff-proxy, discriminated-union-types, server-component-redirect]
key-files:
  created:
    - admin/package.json
    - admin/src/config.ts
    - admin/src/lib/types.ts
    - admin/src/lib/api.ts
    - admin/src/app/api/contents/route.ts
    - admin/src/app/api/contents/[id]/route.ts
    - admin/src/app/api/contents/[id]/approve/route.ts
    - admin/src/app/api/contents/[id]/reject/route.ts
    - admin/.env.local.example
  modified:
    - admin/src/app/layout.tsx
    - admin/src/app/page.tsx
    - admin/src/lib/utils.ts
    - admin/.gitignore
key-decisions:
  - Next.js 15 with App Router, src directory, Tailwind CSS v4
  - shadcn/ui new-york style for clean admin UI
  - BFF proxy pattern: X-API-Key injected server-side, never exposed to browser
  - Snake_case field names in TypeScript types to match FastAPI JSON responses exactly
  - Next.js 15 async params pattern for dynamic route handlers
patterns-established:
  - BFF proxy route pattern (import config, forward with auth header, return upstream response)
  - apiGet/apiPost fetch wrappers for Server Components
  - Discriminated union for LayoutBlock types
duration: 3m
completed: 2026-02-25
---

# Phase 08 Plan 01: Project Scaffold and Infrastructure Summary

Next.js 15 admin dashboard with shadcn/ui, TypeScript types mirroring FastAPI schemas, and BFF proxy routes hiding API key from browser.

## Performance

- Duration: ~3 minutes
- Tasks: 2/2 completed
- Build: clean (0 errors, 0 warnings)

## Accomplishments

1. **Next.js 15 project scaffold** -- Full App Router project with TypeScript, Tailwind CSS v4, ESLint, Geist font, and src directory structure
2. **shadcn/ui component library** -- 8 components installed (table, tabs, badge, button, textarea, skeleton, card, separator) ready for dashboard UI
3. **TypeScript type system** -- Complete mirror of FastAPI schemas: ContentItem, ContentListResponse, MagazineLayout, all 10 LayoutBlock types as discriminated union, supporting types (ImageItem, ProductItem, CelebItem, CreditEntry, KeyValuePair)
4. **BFF proxy layer** -- 4 API routes (list, detail, approve, reject) that forward requests to FastAPI backend with X-API-Key header injected server-side
5. **API client** -- apiGet/apiPost fetch wrappers with error handling for use in Server Components
6. **Root redirect** -- Landing page redirects to /contents via Server Component redirect()

## Task Commits

| Task | Name | Commit | Key Files |
|------|------|--------|-----------|
| 1 | Create Next.js 15 project with shadcn/ui | bdda437 | package.json, layout.tsx, 8 UI components |
| 2 | TypeScript types, config, API client, BFF proxy routes | d6c481e | types.ts, api.ts, config.ts, 4 route files |

## Files Created

- `admin/` -- Complete Next.js 15 project directory
- `admin/src/config.ts` -- API_BASE_URL and ADMIN_API_KEY from env
- `admin/src/lib/types.ts` -- All TypeScript types (ContentItem, MagazineLayout, 10 block types)
- `admin/src/lib/api.ts` -- apiGet and apiPost fetch wrappers
- `admin/src/app/api/contents/route.ts` -- BFF proxy for content list
- `admin/src/app/api/contents/[id]/route.ts` -- BFF proxy for content detail
- `admin/src/app/api/contents/[id]/approve/route.ts` -- BFF proxy for approve action
- `admin/src/app/api/contents/[id]/reject/route.ts` -- BFF proxy for reject action
- `admin/.env.local.example` -- Environment variable template

## Files Modified

- `admin/src/app/layout.tsx` -- Editorial Admin header and clean layout
- `admin/src/app/page.tsx` -- Redirect to /contents
- `admin/src/lib/utils.ts` -- Added formatDate helper
- `admin/.gitignore` -- Added exception for .env.local.example

## Decisions Made

1. **Snake_case TypeScript fields** -- Match FastAPI JSON responses exactly (e.g., `layout_json`, `image_url`, `overlay_title`) instead of converting to camelCase
2. **BFF proxy pattern** -- All backend calls go through Next.js API routes; ADMIN_API_KEY never reaches the browser
3. **Next.js 15 async params** -- Used `params: Promise<{ id: string }>` with await pattern for dynamic route handlers
4. **Tailwind CSS v4** -- create-next-app@15 installs Tailwind v4 by default; shadcn/ui v4 compatible

## Deviations from Plan

1. **[Rule 3 - Blocking] .gitignore .env* pattern blocked .env.local.example** -- The default Next.js .gitignore has `.env*` which blocked committing the example file. Added `!.env.local.example` exception.

## Issues Encountered

None beyond the .gitignore deviation noted above.

## Next Phase Readiness

- All infrastructure ready for 08-02 (content list page) and 08-03 (detail/review page)
- Types, API client, and BFF proxy routes are the foundation all subsequent plans import
- shadcn/ui components available for building dashboard UI
- No blockers for next plans
