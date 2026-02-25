# Phase 8: Admin Dashboard UI - Research

**Researched:** 2026-02-25
**Domain:** Next.js 15 App Router + shadcn/ui + Tailwind CSS admin dashboard consuming FastAPI backend
**Confidence:** HIGH

## Summary

This phase builds a read-only admin dashboard (with approve/reject actions) as a Next.js 15 App Router application inside the `admin/` subdirectory of the existing monorepo. The dashboard consumes the Phase 7 FastAPI admin API (`/api/contents`, `/api/pipeline`), renders Magazine Layout JSON as a high-fidelity preview, and provides approve/reject workflows.

The Phase 7 API is fully implemented and provides: list contents with optional status filter + pagination (`GET /api/contents?status=pending&limit=50&offset=0`), content detail (`GET /api/contents/{id}`), approve (`POST /api/contents/{id}/approve`), reject (`POST /api/contents/{id}/reject`), and pipeline trigger (`POST /api/pipeline/trigger`). Authentication uses `X-API-Key` header with dev-mode bypass when `ADMIN_API_KEY` is not configured.

The Layout JSON schema has 10 block types (hero, headline, body_text, image_gallery, pull_quote, product_showcase, celeb_feature, divider, hashtag_bar, credits), each with a `type` discriminator field. The dashboard must render each block type as a distinct visual component with magazine-style typography and spacing.

**Primary recommendation:** Use Next.js 15 App Router with Route Handlers as a BFF (Backend for Frontend) proxy layer to the FastAPI backend. Server Components fetch data via the proxy for the initial page load (list and detail pages). Client Components handle interactive mutations (approve/reject). Use shadcn/ui's Table, Tabs, Badge, Button, Textarea, and Skeleton components. Build a custom `BlockRenderer` component that maps each Layout JSON block `type` to a styled React component.

**Important note on Next.js version:** Next.js 16 is the current stable release (16.2 as of Feb 2026). The user has locked the decision to use Next.js 15. Use `pnpm add next@15 react@19 react-dom@19` to pin the version. All patterns in this research are compatible with Next.js 15 App Router.

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| next | 15.x (pinned) | React framework with App Router, SSR, Route Handlers | User decision; App Router provides file-based routing, Server Components, Route Handlers for BFF proxy |
| react / react-dom | 19.x | UI rendering | Required by Next.js 15; stable release |
| tailwindcss | 4.x | Utility-first CSS | User decision; pairs with shadcn/ui |
| @shadcn/ui (via CLI) | latest | Pre-built accessible component library | User decision; provides Table, Tabs, Badge, Button, Textarea, Skeleton, etc. |
| typescript | 5.x | Type safety | Next.js default; critical for Layout JSON type definitions |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| @tanstack/react-table | 8.x | Headless table logic (sorting, pagination) | Powers shadcn/ui Data Table component; needed for content list |
| lucide-react | latest | Icon library | Default with shadcn/ui; used for navigation arrows, status icons |
| clsx / tailwind-merge | latest | Conditional class merging | Installed by shadcn/ui init; used in component styling |
| date-fns | latest | Date formatting | Format created_at/updated_at in table and detail views |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Next.js 15 | Next.js 16 (current stable) | 16 has Turbopack stable + React Compiler; but user locked v15, fully sufficient for this use case |
| Route Handler proxy | next.config.js rewrites | Rewrites are simpler but can't inject headers (API key) or transform responses |
| @tanstack/react-table | Simple HTML table | Loses pagination/sorting for free; shadcn Data Table is built on tanstack |
| Server Components for data | Client-side SWR/react-query | Server Components simpler for read-heavy dashboard; mutations handled client-side |

**Installation:**
```bash
# From project root
mkdir admin && cd admin

# Create Next.js 15 project
pnpm create next-app@15 . --typescript --tailwind --eslint --app --src-dir --import-alias "@/*" --yes

# Pin Next.js 15 explicitly (create-next-app may install latest)
pnpm add next@15 react@19 react-dom@19

# Initialize shadcn/ui
pnpm dlx shadcn@latest init

# Add required shadcn components
pnpm dlx shadcn@latest add table tabs badge button textarea skeleton card separator

# Add tanstack table for data table
pnpm add @tanstack/react-table

# Add date formatting
pnpm add date-fns
```

## Architecture Patterns

### Recommended Project Structure
```
admin/
  src/
    app/
      layout.tsx              # Root layout (font, global styles, header)
      page.tsx                # Redirect to /contents or show dashboard home
      contents/
        page.tsx              # Content list page (Server Component)
        [id]/
          page.tsx            # Content detail + preview (Server Component shell)
          actions.tsx         # Client Component for approve/reject buttons
      api/
        contents/
          route.ts            # BFF proxy: GET -> FastAPI /api/contents
          [id]/
            route.ts          # BFF proxy: GET -> FastAPI /api/contents/{id}
            approve/
              route.ts        # BFF proxy: POST -> FastAPI /api/contents/{id}/approve
            reject/
              route.ts        # BFF proxy: POST -> FastAPI /api/contents/{id}/reject
    components/
      ui/                     # shadcn/ui generated components
      content-table.tsx       # Data table with tabs and pagination
      content-status-badge.tsx # Status badge (color-coded)
      block-renderer.tsx      # Layout JSON -> React components dispatcher
      blocks/                 # Individual block renderers
        hero-block.tsx
        headline-block.tsx
        body-text-block.tsx
        image-gallery-block.tsx
        pull-quote-block.tsx
        product-showcase-block.tsx
        celeb-feature-block.tsx
        divider-block.tsx
        hashtag-bar-block.tsx
        credits-block.tsx
      json-panel.tsx          # Collapsible raw JSON viewer
      sticky-action-bar.tsx   # Sticky top bar with back, status, actions
      reject-form.tsx         # Inline rejection reason textarea
    lib/
      api.ts                  # API client (fetch wrapper with base URL + headers)
      types.ts                # TypeScript types mirroring API schemas
      utils.ts                # cn() utility from shadcn, date formatters
    config.ts                 # Environment variables (API base URL, API key)
  next.config.ts              # Next.js config
  tailwind.config.ts          # Tailwind config (extended with shadcn theme)
  components.json             # shadcn/ui config
  package.json
  tsconfig.json
```

### Pattern 1: BFF Proxy via Route Handlers
**What:** Next.js Route Handlers forward API calls to the FastAPI backend, injecting the API key server-side so it never reaches the browser.
**When to use:** Every API call from the dashboard to the FastAPI backend.
**Why:** Avoids CORS issues (same-origin requests), keeps API key server-side, allows response transformation if needed.

```typescript
// admin/src/app/api/contents/route.ts
import { NextRequest, NextResponse } from 'next/server';

const API_BASE = process.env.API_BASE_URL || 'http://localhost:8000';
const API_KEY = process.env.ADMIN_API_KEY || '';

export async function GET(request: NextRequest) {
  const searchParams = request.nextUrl.searchParams;
  const url = new URL('/api/contents', API_BASE);

  // Forward query params (status, limit, offset)
  searchParams.forEach((value, key) => url.searchParams.set(key, value));

  const res = await fetch(url.toString(), {
    headers: {
      'X-API-Key': API_KEY,
      'Content-Type': 'application/json',
    },
    cache: 'no-store', // Always fresh data for admin dashboard
  });

  const data = await res.json();
  return NextResponse.json(data, { status: res.status });
}
```

### Pattern 2: Server Component Data Fetching
**What:** Page components are async Server Components that fetch data server-side, eliminating client-side loading spinners for initial page load.
**When to use:** List page and detail page initial data load.

```typescript
// admin/src/app/contents/page.tsx
import { ContentTable } from '@/components/content-table';

interface SearchParams {
  status?: string;
  page?: string;
}

export default async function ContentsPage({
  searchParams,
}: {
  searchParams: Promise<SearchParams>;
}) {
  const params = await searchParams;
  const status = params.status || undefined;
  const page = parseInt(params.page || '1', 10);
  const limit = 20;
  const offset = (page - 1) * limit;

  // Fetch from own Route Handler (same-origin, no CORS)
  const res = await fetch(
    `${process.env.NEXT_PUBLIC_BASE_URL}/api/contents?` +
      new URLSearchParams({
        ...(status && { status }),
        limit: String(limit),
        offset: String(offset),
      }),
    { cache: 'no-store' }
  );
  const data = await res.json();

  return <ContentTable items={data.items} total={data.total} page={page} limit={limit} />;
}
```

### Pattern 3: Block Renderer (Layout JSON -> React Components)
**What:** A dispatcher component that maps each block `type` to a dedicated React component for high-fidelity magazine preview rendering.
**When to use:** Detail page content preview.

```typescript
// admin/src/components/block-renderer.tsx
import { HeroBlock } from './blocks/hero-block';
import { HeadlineBlock } from './blocks/headline-block';
import { BodyTextBlock } from './blocks/body-text-block';
// ... other block imports

type LayoutBlock = { type: string; [key: string]: unknown };

const BLOCK_MAP: Record<string, React.ComponentType<{ block: any }>> = {
  hero: HeroBlock,
  headline: HeadlineBlock,
  body_text: BodyTextBlock,
  image_gallery: ImageGalleryBlock,
  pull_quote: PullQuoteBlock,
  product_showcase: ProductShowcaseBlock,
  celeb_feature: CelebFeatureBlock,
  divider: DividerBlock,
  hashtag_bar: HashtagBarBlock,
  credits: CreditsBlock,
};

export function BlockRenderer({ blocks }: { blocks: LayoutBlock[] }) {
  return (
    <article className="max-w-3xl mx-auto space-y-8">
      {blocks.map((block, index) => {
        const Component = BLOCK_MAP[block.type];
        if (!Component) {
          return (
            <div key={index} className="p-4 border border-dashed border-orange-300 rounded bg-orange-50">
              <p className="text-sm text-orange-600">Unknown block type: {block.type}</p>
            </div>
          );
        }
        return <Component key={index} block={block} />;
      })}
    </article>
  );
}
```

### Pattern 4: Client-Side Mutations with Optimistic UI
**What:** Approve/reject actions use client components with fetch() to call the BFF proxy. After success, update the local state immediately (optimistic) and use `router.refresh()` to revalidate server data.
**When to use:** Approve/reject buttons on detail page.

```typescript
// admin/src/app/contents/[id]/actions.tsx
'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/textarea';

interface ActionBarProps {
  contentId: string;
  status: string;
}

export function ActionBar({ contentId, status }: ActionBarProps) {
  const router = useRouter();
  const [currentStatus, setCurrentStatus] = useState(status);
  const [showRejectForm, setShowRejectForm] = useState(false);
  const [rejectReason, setRejectReason] = useState('');
  const [isLoading, setIsLoading] = useState(false);

  const isPending = currentStatus === 'pending';

  async function handleApprove() {
    setIsLoading(true);
    try {
      const res = await fetch(`/api/contents/${contentId}/approve`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({}),
      });
      if (res.ok) {
        setCurrentStatus('approved');
        router.refresh(); // Revalidate server component data
      }
    } finally {
      setIsLoading(false);
    }
  }

  async function handleReject() {
    if (!rejectReason.trim()) return;
    setIsLoading(true);
    try {
      const res = await fetch(`/api/contents/${contentId}/reject`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ reason: rejectReason }),
      });
      if (res.ok) {
        setCurrentStatus('rejected');
        setShowRejectForm(false);
        router.refresh();
      }
    } finally {
      setIsLoading(false);
    }
  }

  return (
    <div className="sticky top-0 z-50 bg-white border-b px-6 py-3 flex items-center gap-4">
      {/* Back button, status badge, action buttons */}
    </div>
  );
}
```

### Pattern 5: Image Placeholders
**What:** Since actual images are not available (URLs are placeholders), render colored boxes with type labels instead.
**When to use:** Any block that references `image_url`.

```typescript
// admin/src/components/blocks/hero-block.tsx
export function HeroBlock({ block }: { block: { image_url: string; overlay_title?: string; overlay_subtitle?: string } }) {
  return (
    <div className="relative w-full aspect-[16/9] bg-slate-200 rounded-lg overflow-hidden flex items-center justify-center">
      <span className="text-slate-500 text-sm font-medium uppercase tracking-wider">
        Hero Image
      </span>
      {block.overlay_title && (
        <div className="absolute inset-0 flex flex-col items-center justify-center bg-black/30 text-white p-6">
          <h1 className="text-3xl font-bold">{block.overlay_title}</h1>
          {block.overlay_subtitle && (
            <p className="text-lg mt-2 opacity-90">{block.overlay_subtitle}</p>
          )}
        </div>
      )}
    </div>
  );
}
```

### Anti-Patterns to Avoid
- **Calling FastAPI directly from browser:** Exposes API key, creates CORS issues. Always proxy through Next.js Route Handlers.
- **Using Server Actions for data fetching:** Server Actions are for mutations and execute sequentially. Use Server Components for reads and client fetch for mutations.
- **Rendering layout blocks with dangerouslySetInnerHTML:** Layout JSON contains structured data, not HTML. Render with React components.
- **Fetching data in client components for initial page load:** Use Server Components for initial data. Client components only for interactive state updates.
- **Over-abstracting block components:** Each block type has distinct fields. Keep block components simple and type-specific, not generic.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Data table with sorting/pagination | Custom table logic | shadcn/ui Data Table + @tanstack/react-table | Handles keyboard nav, pagination state, sorting, column visibility |
| Status badge styling | Manual CSS per status | shadcn Badge with variant map | Consistent, accessible, theme-aware |
| Loading skeleton | Custom shimmer animation | shadcn Skeleton | Accessible, matches component shapes |
| Form validation (reject reason) | Manual state checks | HTML required attribute + controlled state | Simple enough for single textarea; no need for form library |
| API client | axios or custom class | Native fetch + thin wrapper | Next.js extends fetch with caching; no extra dependency needed |
| CSS framework | Custom CSS | Tailwind CSS utility classes | User decision; pairs with shadcn; rapid iteration |

**Key insight:** shadcn/ui provides copy-paste components (not a package import). Components live in `src/components/ui/` and can be freely modified. This means no version lock-in and full control over rendering.

## Common Pitfalls

### Pitfall 1: CORS Between Next.js Dev Server and FastAPI
**What goes wrong:** Browser fetch to `http://localhost:8000/api/contents` fails with CORS error.
**Why it happens:** Next.js dev server runs on port 3000, FastAPI on port 8000. Cross-origin requests are blocked by default.
**How to avoid:** Use Route Handlers as a BFF proxy. All browser requests go to `/api/contents` (same origin, port 3000), which the Route Handler forwards to `localhost:8000`. No CORS configuration needed.
**Warning signs:** `Access-Control-Allow-Origin` errors in browser console.

### Pitfall 2: Server Component Fetching Own Route Handlers
**What goes wrong:** Server Components fetching from `/api/contents` fail at build time because there's no server running.
**Why it happens:** During `next build`, Server Components pre-render. Fetching from own Route Handlers requires a running server.
**How to avoid:** Use absolute URL with `process.env.NEXT_PUBLIC_BASE_URL` or fetch from the FastAPI backend directly in Server Components (since they run server-side, no CORS issue). Alternatively, use `export const dynamic = 'force-dynamic'` to skip pre-rendering.
**Warning signs:** Build failures with "fetch failed" errors.

### Pitfall 3: Stale Data After Approve/Reject
**What goes wrong:** User approves content, but the list page still shows "pending" status when navigating back.
**Why it happens:** Next.js caches Server Component data. `router.back()` uses cached page.
**How to avoid:** After mutation, call `router.refresh()` to revalidate the current page data. For the list page, ensure `cache: 'no-store'` on fetch or use `revalidatePath` from a Server Action.
**Warning signs:** Status not updating after navigation.

### Pitfall 4: Missing `use client` Directive
**What goes wrong:** Component using `useState`, `useRouter`, or event handlers throws error about hooks in Server Components.
**Why it happens:** In App Router, all components are Server Components by default. Client-side hooks require explicit opt-in.
**How to avoid:** Add `'use client'` directive at the top of any component that uses React hooks, browser APIs, or event handlers (onClick, onChange, etc.).
**Warning signs:** "useState is not a function" or "Event handlers cannot be passed to Server Components" errors.

### Pitfall 5: Layout JSON Type Mismatches
**What goes wrong:** Block renderer crashes because a field is undefined or has unexpected type.
**Why it happens:** AI-generated Layout JSON may have optional fields missing, empty arrays, or unexpected values.
**How to avoid:** Use defensive rendering with optional chaining (`?.`) and fallback values. Each block component should handle missing/empty data gracefully with placeholder content.
**Warning signs:** "Cannot read property of undefined" in production.

### Pitfall 6: Approve Action Taking Too Long
**What goes wrong:** Approve button appears frozen. User clicks multiple times.
**Why it happens:** The FastAPI approve endpoint resumes the LangGraph pipeline (calls `graph.ainvoke(Command(resume=...))`), which may take several seconds for the publish node to complete.
**How to avoid:** Show loading spinner on button immediately. Disable button after first click. Consider optimistic UI update (change badge to "approved" immediately, revert on error).
**Warning signs:** Multiple approve requests in API logs.

## Code Examples

### TypeScript Types Mirroring API Schemas
```typescript
// admin/src/lib/types.ts
// Source: Mirrors src/editorial_ai/api/schemas.py ContentResponse

export interface ContentItem {
  id: string;
  thread_id: string;
  status: 'pending' | 'approved' | 'rejected' | 'published';
  title: string;
  keyword: string;
  layout_json: MagazineLayout;
  review_summary: string | null;
  rejection_reason: string | null;
  admin_feedback: string | null;
  created_at: string;
  updated_at: string;
  published_at: string | null;
}

export interface ContentListResponse {
  items: ContentItem[];
  total: number;
}

// Layout JSON types — mirrors src/editorial_ai/models/layout.py
export interface MagazineLayout {
  schema_version: string;
  title: string;
  subtitle?: string;
  keyword: string;
  blocks: LayoutBlock[];
  created_at?: string;
  metadata?: { key: string; value: string }[];
}

export type LayoutBlock =
  | HeroBlock
  | HeadlineBlock
  | BodyTextBlock
  | ImageGalleryBlock
  | PullQuoteBlock
  | ProductShowcaseBlock
  | CelebFeatureBlock
  | DividerBlock
  | HashtagBarBlock
  | CreditsBlock;

export interface HeroBlock {
  type: 'hero';
  image_url: string;
  overlay_title?: string;
  overlay_subtitle?: string;
}

export interface HeadlineBlock {
  type: 'headline';
  text: string;
  level: 1 | 2 | 3;
}

export interface BodyTextBlock {
  type: 'body_text';
  paragraphs: string[];
}

export interface ImageGalleryBlock {
  type: 'image_gallery';
  images: { url: string; alt?: string; caption?: string }[];
  layout_style: 'grid' | 'carousel' | 'masonry';
}

export interface PullQuoteBlock {
  type: 'pull_quote';
  quote: string;
  attribution?: string;
}

export interface ProductShowcaseBlock {
  type: 'product_showcase';
  products: {
    product_id?: string;
    name: string;
    brand?: string;
    image_url?: string;
    description?: string;
  }[];
}

export interface CelebFeatureBlock {
  type: 'celeb_feature';
  celebs: {
    celeb_id?: string;
    name: string;
    image_url?: string;
    description?: string;
  }[];
}

export interface DividerBlock {
  type: 'divider';
  style: 'line' | 'space' | 'ornament';
}

export interface HashtagBarBlock {
  type: 'hashtag_bar';
  hashtags: string[];
}

export interface CreditsBlock {
  type: 'credits';
  entries: { role: string; name: string }[];
}
```

### Status Badge Component
```typescript
// admin/src/components/content-status-badge.tsx
import { Badge } from '@/components/ui/badge';

const STATUS_VARIANTS: Record<string, { variant: 'default' | 'secondary' | 'destructive' | 'outline'; label: string }> = {
  pending: { variant: 'secondary', label: 'Pending' },
  approved: { variant: 'default', label: 'Approved' },
  rejected: { variant: 'destructive', label: 'Rejected' },
  published: { variant: 'outline', label: 'Published' },
};

export function ContentStatusBadge({ status }: { status: string }) {
  const config = STATUS_VARIANTS[status] || { variant: 'outline' as const, label: status };
  return <Badge variant={config.variant}>{config.label}</Badge>;
}
```

### API Client Wrapper
```typescript
// admin/src/lib/api.ts
const API_BASE = process.env.NEXT_PUBLIC_BASE_URL || 'http://localhost:3000';

export async function apiGet<T>(path: string, params?: Record<string, string>): Promise<T> {
  const url = new URL(path, API_BASE);
  if (params) {
    Object.entries(params).forEach(([key, value]) => {
      if (value !== undefined) url.searchParams.set(key, value);
    });
  }
  const res = await fetch(url.toString(), { cache: 'no-store' });
  if (!res.ok) throw new Error(`API error: ${res.status}`);
  return res.json();
}

export async function apiPost<T>(path: string, body?: unknown): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: body ? JSON.stringify(body) : undefined,
  });
  if (!res.ok) throw new Error(`API error: ${res.status}`);
  return res.json();
}
```

### Collapsible JSON Panel
```typescript
// admin/src/components/json-panel.tsx
'use client';

import { useState } from 'react';
import { Button } from '@/components/ui/button';

export function JsonPanel({ data }: { data: unknown }) {
  const [isOpen, setIsOpen] = useState(false);

  return (
    <div className="mt-8 border rounded-lg">
      <Button
        variant="ghost"
        className="w-full justify-between"
        onClick={() => setIsOpen(!isOpen)}
      >
        Raw JSON
        <span>{isOpen ? 'Hide' : 'Show'}</span>
      </Button>
      {isOpen && (
        <pre className="p-4 bg-slate-950 text-slate-100 text-xs overflow-auto max-h-96 rounded-b-lg">
          {JSON.stringify(data, null, 2)}
        </pre>
      )}
    </div>
  );
}
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Pages Router (`getServerSideProps`) | App Router (async Server Components) | Next.js 13+ (stable in 14/15) | Simpler data fetching, no prop drilling for server data |
| API Routes (`pages/api/`) | Route Handlers (`app/api/.../route.ts`) | Next.js 13+ | Web standard Request/Response API |
| npm/yarn component packages | shadcn/ui copy-paste CLI | 2023+ | Full control, no version lock-in, customizable |
| CSS Modules / styled-components | Tailwind CSS utility classes | Industry-wide shift 2022+ | Faster iteration, consistent design system |
| `@app.on_event("startup")` | `lifespan` context manager | FastAPI 0.93+ | (Backend reference for dev workflow) |
| `middleware.ts` for proxying | `proxy.ts` file convention | Next.js 16+ | Next.js 15 uses middleware.ts; proxy.ts is v16 only |

**Deprecated/outdated in Next.js 15:**
- `getServerSideProps` / `getStaticProps`: Replaced by async Server Components in App Router
- `pages/api/`: Replaced by Route Handlers (`app/api/.../route.ts`)
- `proxy.ts` file convention: This is Next.js 16+ only. Next.js 15 uses `middleware.ts` or Route Handlers

**Note on Next.js 15 vs 16:**
- Next.js 16 is the current stable (16.2). User locked v15.
- Key differences: 16 has stable Turbopack for build, React Compiler, `proxy.ts` convention. These are nice-to-haves but not needed for this phase.
- Next.js 15 is fully capable for this dashboard. No feature gap that affects implementation.

## Open Questions

1. **Server Component vs Client fetch for list page**
   - What we know: Server Components can fetch data server-side. But the list page has interactive tabs that filter by status, which triggers URL changes.
   - What's unclear: Should tab clicks trigger full page navigation (Server Component re-render) or client-side re-fetch?
   - Recommendation: Use URL search params for tab state (`?status=pending`). Tab clicks navigate via `router.push()`, which re-renders the Server Component with new data. This keeps the URL bookmarkable and avoids client state management for filter state. The list page itself remains a Server Component.

2. **Approve endpoint latency**
   - What we know: `POST /api/contents/{id}/approve` calls `graph.ainvoke(Command(resume=...))` which resumes the full pipeline (publish node execution).
   - What's unclear: How long does this take? If >2-3 seconds, the UI will feel sluggish.
   - Recommendation: Implement optimistic UI update. Change badge to "approved" immediately on click, show a subtle loading indicator, revert on error. The actual status will be confirmed when the API responds and `router.refresh()` revalidates.

3. **FastAPI and Next.js dev server coordination**
   - What we know: Two dev servers need to run simultaneously (FastAPI on :8000, Next.js on :3000).
   - What's unclear: Best DX for starting both.
   - Recommendation: Document in README or add a script. Use `API_BASE_URL=http://localhost:8000` env var in `admin/.env.local`. Consider adding a root-level script that starts both (e.g., using `concurrently` or just two terminal windows).

## Recommendations for Claude's Discretion Areas

### Color Scheme and Typography
- Use shadcn/ui default theme (neutral grays) as the base -- clean, professional admin aesthetic
- Status colors: pending = amber/yellow, approved = green, rejected = red, published = blue/slate
- Typography: system font stack (Inter or Geist from Next.js defaults) -- fast loading, professional
- Magazine preview area: use serif font (e.g., Georgia, Playfair Display via Google Fonts) for headlines to evoke editorial feel. Body text in sans-serif.

### Loading States and Skeleton Design
- List page: Table skeleton with 5 rows of animated shimmer bars matching column widths
- Detail page: Skeleton blocks matching approximate layout shapes (tall rectangle for hero, thin bar for headline, paragraph blocks for body)
- Mutation loading: Button shows spinner icon, becomes disabled, text changes to "Approving..." / "Rejecting..."

### Error State Handling
- API fetch failures: Show centered error card with message and "Retry" button
- Network errors: Toast notification at bottom of screen (use shadcn Sonner/Toast)
- 404 content: Full page "Content not found" with link back to list
- Approve/reject failure: Toast error with message, buttons re-enabled for retry

### Table Sorting
- Default sort: created_at descending (newest first)
- Optional client-side column sorting via @tanstack/react-table (title, status, created_at, keyword)
- No server-side sorting in V1 (API doesn't support sort params); acceptable for admin dashboard scale

### Mobile Responsiveness
- Dashboard is primarily a desktop tool, but make it usable on tablet
- Table: horizontal scroll on small screens
- Detail page: stack sticky bar elements vertically on narrow screens
- Preview: single-column layout that naturally adapts (max-w-3xl with mx-auto)

## Sources

### Primary (HIGH confidence)
- Next.js official docs: Installation, App Router, Route Handlers, Server/Client Components -- https://nextjs.org/docs/app/getting-started/installation
- Next.js BFF guide -- https://nextjs.org/docs/app/guides/backend-for-frontend
- shadcn/ui official docs: Next.js installation, component library -- https://ui.shadcn.com/docs/installation/next
- shadcn/ui Data Table: @tanstack/react-table integration -- https://ui.shadcn.com/docs/components/radix/data-table
- Existing codebase: Phase 7 API (`api/routes/admin.py`, `api/schemas.py`, `services/content_service.py`, `models/layout.py`) -- verified directly

### Secondary (MEDIUM confidence)
- Next.js 16 release blog (confirms v16 is current stable, v15 still supported) -- https://nextjs.org/blog/next-16
- Next.js data fetching patterns (Server vs Client Components, 2026) -- https://nextjs.org/docs/app/getting-started/fetching-data

### Tertiary (LOW confidence)
- None -- all critical patterns verified with official docs or codebase inspection

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- all libraries well-established; Next.js 15 + shadcn/ui is a proven combination; API contract verified from codebase
- Architecture: HIGH -- BFF proxy pattern is officially documented by Next.js; block renderer pattern is standard React composition
- Pitfalls: HIGH -- CORS, Server/Client Component boundaries, and stale data are well-documented Next.js gotchas

**Research date:** 2026-02-25
**Valid until:** 2026-03-25 (Next.js 15 is stable; shadcn/ui is stable)
