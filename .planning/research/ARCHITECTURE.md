# Architecture Patterns

**Domain:** Pipeline Observability + Dynamic Magazine Rendering + E2E Setup for Editorial AI Worker v1.1
**Researched:** 2026-02-26
**Overall confidence:** HIGH (all three features integrate with well-understood existing components)

---

## Current Architecture Snapshot

```
                    LangGraph StateGraph (7 nodes)
  START -> curation -> source -> editorial -> enrich -> review -+-> admin_gate -> publish -> END
                                    ^                           |       |
                                    |     (revision_count < 3)  |       |
                                    +---------------------------+       |
                                    |       (revision_requested)        |
                                    +-----------------------------------+
```

**Backend:** FastAPI + LangGraph + Supabase (REST API) + AsyncPostgresSaver (checkpointing)
**Frontend:** Next.js 15 + React 19 + shadcn/ui + Tailwind CSS 4 + block-based renderer (10 block types)
**LLM:** Gemini 2.5 Flash via `langchain-google-genai`
**State:** `EditorialPipelineState` (TypedDict, lean state principle -- IDs/references only)
**Admin Dashboard:** `/admin/` directory, Next.js 15 with Turbopack, pages for content list + detail with block rendering + approve/reject flow

---

## Recommended Architecture: Three Feature Pillars

### Overview

The three v1.1 features integrate at different layers of the existing stack:

```
                          +--------------------------+
                          |    Admin Dashboard       |
                          |    (Next.js 15)          |
                          +-----+----------+---------+
                                |          |
                  [Pipeline Timeline] [Enhanced Block Renderer]
                                |          |
                          +-----+----------+---------+
                          |    FastAPI Admin API      |
                          |    + /api/pipeline/runs   |
                          +-----+----------+---------+
                                |          |
                    [Run Log API]   [Content API (existing)]
                                |          |
                          +-----+----------+---------+
                          |    LangGraph Pipeline     |
                          |    + node_wrapper()       |
                          +-----+----------+---------+
                                |          |
                    [LangSmith]   [Supabase]
                       (SaaS)    [+ pipeline_node_runs table]
```

---

## Pillar 1: Pipeline Observability

### Integration Strategy: Two-Tier Approach

**Tier 1 (External/SaaS): LangSmith auto-tracing -- already partially configured.**

The project already has LangSmith settings in `src/editorial_ai/config.py` (lines 38-44):
- `langsmith_tracing: bool` (default False)
- `langsmith_api_key: str | None`
- `langsmith_project: str` (default "editorial-ai-worker")

The `langsmith` package is already in dependencies (pyproject.toml: `langsmith>=0.7.5`).

**What it gives for free when `LANGSMITH_TRACING=true`:**
- Full trace tree per pipeline run (every node, every LLM call)
- Token usage per LLM call
- Latency per step
- Input/output of each node
- Conditional edge decisions
- Async collection, typically 1-5ms overhead

**For non-LangChain functions** (e.g., Supabase queries in `source_node`), use the `@traceable` decorator from `langsmith` to include them in the trace tree.

**Confidence: HIGH** -- verified via [LangSmith docs](https://docs.langchain.com/langsmith/trace-with-langgraph). LangChain runnables within graph nodes auto-trace. LangSmith env vars are already defined in the Settings class.

**Tier 2 (Internal/Supabase): Per-node execution logging for the admin dashboard.**

LangSmith is great for developers but not for admin users. The admin dashboard needs its own observability data showing pipeline progress and per-node timing.

### New Component: `node_wrapper` Decorator

**File:** `src/editorial_ai/observability.py`

```python
import time
import functools
from datetime import datetime, timezone

async def save_node_run(run_data: dict) -> None:
    """Fire-and-forget save to pipeline_node_runs table."""
    from editorial_ai.services.supabase_client import get_supabase_client
    client = await get_supabase_client()
    await client.table("pipeline_node_runs").insert(run_data).execute()

def node_wrapper(node_name: str):
    """Decorator that wraps a LangGraph node function with execution logging.

    Captures: start time, duration, success/error status.
    Writes to pipeline_node_runs table (fire-and-forget).
    Never breaks the pipeline -- all observability errors are silently caught.
    """
    def decorator(fn):
        @functools.wraps(fn)
        async def wrapper(state):
            thread_id = state.get("thread_id") or "unknown"
            started_at = datetime.now(timezone.utc)
            start = time.monotonic()
            error_msg = None
            try:
                result = await fn(state)
                return result
            except Exception as e:
                error_msg = f"{type(e).__name__}: {e!s}"
                raise
            finally:
                duration_ms = int((time.monotonic() - start) * 1000)
                run_data = {
                    "thread_id": thread_id,
                    "node_name": node_name,
                    "started_at": started_at.isoformat(),
                    "duration_ms": duration_ms,
                    "status": "error" if error_msg else "success",
                    "error_message": error_msg,
                    "revision_count": state.get("revision_count", 0),
                }
                try:
                    await save_node_run(run_data)
                except Exception:
                    pass  # observability must never break the pipeline
        return wrapper
    return decorator
```

### Where to Hook: `graph.py` `build_graph()`

**Do NOT modify individual node files.** Instead, wrap at graph construction time in `src/editorial_ai/graph.py`:

```python
# In build_graph():
from editorial_ai.observability import node_wrapper

nodes: dict[str, Callable] = {
    "curation": node_wrapper("curation")(curation_node),
    "source": node_wrapper("source")(source_node),
    "editorial": node_wrapper("editorial")(editorial_node),
    "enrich": node_wrapper("enrich")(enrich_from_posts_node),
    "review": node_wrapper("review")(review_node),
    "admin_gate": node_wrapper("admin_gate")(admin_gate),
    "publish": node_wrapper("publish")(publish_node),
}
```

This approach:
- Keeps node implementations pure (no observability coupling)
- Makes the wrapper trivially removable or swappable
- Follows the existing `node_overrides` pattern already in `build_graph()`
- Tests can still use `node_overrides` to bypass wrapping

### New Supabase Table: `pipeline_node_runs`

```sql
CREATE TABLE pipeline_node_runs (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    thread_id TEXT NOT NULL,
    node_name TEXT NOT NULL,
    started_at TIMESTAMPTZ NOT NULL,
    duration_ms INTEGER NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('success', 'error')),
    error_message TEXT,
    revision_count INTEGER DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX idx_node_runs_thread ON pipeline_node_runs(thread_id);
CREATE INDEX idx_node_runs_created ON pipeline_node_runs(created_at DESC);
```

### New API Endpoints

Add to `src/editorial_ai/api/routes/pipeline.py`:

```
GET /api/pipeline/runs/{thread_id}  -> List of node execution records for a thread
GET /api/pipeline/runs/recent       -> Recent pipeline runs with aggregated stats
```

### Admin Dashboard: Pipeline Timeline Component

**File:** `admin/src/components/pipeline-timeline.tsx`

New component on the content detail page showing node execution as a horizontal timeline:

```
[curation: 2.3s] -> [source: 1.1s] -> [editorial: 8.5s] -> [enrich: 3.2s] -> [review: 4.1s] -> [admin_gate: waiting]
   OK                  OK               OK                   OK               OK
```

Visual: horizontal steps with colored status indicators (green=success, red=error, gray=pending/waiting).

**Integration point:** Content detail page (`admin/src/app/contents/[id]/page.tsx`) already has the `thread_id` from the content object. Use it to fetch `/api/pipeline/runs/{thread_id}`.

### Confidence Assessment

| Decision | Confidence | Rationale |
|----------|-----------|-----------|
| LangSmith auto-trace via env vars | HIGH | Already configured in config.py, verified in official docs |
| `node_wrapper` decorator pattern | HIGH | Standard Python pattern, no LangGraph API dependency |
| Supabase table for admin-visible logs | HIGH | Consistent with existing data model (editorial_contents uses same Supabase pattern) |
| Fire-and-forget save in finally block | MEDIUM | Could lose logs on process crash mid-save, but pipeline reliability > observability |

---

## Pillar 2: Dynamic Magazine Renderer

### Current State Analysis

The admin dashboard **already has** a fully functional block renderer:
- `admin/src/components/block-renderer.tsx` -- main dispatcher using `BLOCK_MAP` record
- `admin/src/components/blocks/` -- 10 individual block components (hero, headline, body_text, image_gallery, pull_quote, product_showcase, celeb_feature, divider, hashtag_bar, credits)
- Content detail page (`admin/src/app/contents/[id]/page.tsx` line 106) already renders `<BlockRenderer blocks={content.layout_json?.blocks ?? []} />`
- TypeScript types (`admin/src/lib/types.ts`) mirror Python Pydantic models 1:1

**Key finding: The "dynamic magazine renderer" is essentially already built.** The existing block components use placeholder visuals (gray boxes with text labels instead of actual images). The work is enhancement, not creation.

### What Needs Enhancement

#### 1. Image Rendering (Currently Placeholder)

`hero-block.tsx` renders a gray box with "Hero Image" text instead of the actual `block.image_url`. Same for `product-showcase-block.tsx` (blue boxes with "Product Photo") and `celeb-feature-block.tsx`.

**Fix:** Render actual `<img>` or Next.js `<Image>` with fallback to current placeholder:

```tsx
// hero-block.tsx enhancement
{block.image_url ? (
  <img
    src={block.image_url}
    alt={block.overlay_title ?? "Hero"}
    className="h-full w-full object-cover"
  />
) : (
  <div className="flex h-full items-center justify-center text-sm text-slate-500">
    No image available
  </div>
)}
```

Note: Use `<img>` not `next/image` for external URLs unless you configure `remotePatterns` in `next.config.ts`. The image URLs come from Supabase/external sources with unknown domains.

#### 2. Gallery Layout Styles

`image_gallery` block has `layout_style: "grid" | "carousel" | "masonry"` in the TypeScript type but the current component likely only renders grid. Carousel and masonry need implementation.

**Recommendation:** CSS-only approach with Tailwind CSS 4:
- **Grid:** Already works (CSS Grid)
- **Carousel:** `overflow-x-auto scroll-snap-x snap-mandatory` with `snap-start` on children
- **Masonry:** CSS `columns-2 gap-4` (native CSS columns) or CSS Grid with `masonry` layout

No external library needed.

#### 3. Magazine-Quality Typography and Spacing

The current `max-w-3xl space-y-8` container (block-renderer.tsx line 39) is functional but not magazine-quality. Enhancements:
- Hero block: full-bleed (break out of `max-w-3xl`)
- Pull quotes: larger font, decorative left border or large quotation marks
- Body text: proper leading (`leading-relaxed` or `leading-loose`), optional drop cap for first paragraph
- Divider ornaments: the `style: "ornament"` variant needs visual implementation (currently just renders a line)
- Credits: magazine-style footer with small caps

#### 4. Responsive Preview Mode (New)

Add device-width toggle in the content detail page for editors to preview how the magazine looks at different breakpoints.

**New component:** `admin/src/components/preview-mode-toggle.tsx`

```tsx
// Wraps BlockRenderer in an iframe-like container with width constraints
type PreviewMode = "mobile" | "tablet" | "desktop";
// mobile: max-w-sm, tablet: max-w-2xl, desktop: full width
```

### Architecture Decision: CSS-Heavy vs Component Library

**Recommendation: CSS-heavy with Tailwind CSS 4.**

Rationale:
- Already using Tailwind CSS 4 + shadcn/ui -- no new dependencies needed
- Magazine layouts are inherently visual/CSS-heavy (typography, spacing, bleed)
- Component libraries (MUI, Chakra) add abstraction layers that fight magazine styling
- The block components are well-structured with clean TypeScript types matching Python Pydantic 1:1
- shadcn/ui provides base components (Card, Badge, etc.) already in use

### Component Boundaries

**No new block components needed. Only enhancement of existing 10 blocks:**

| Component | File | Status | Enhancement Needed |
|-----------|------|--------|-------------------|
| `block-renderer.tsx` | `admin/src/components/block-renderer.tsx` | EXISTS | Add preview mode wrapper |
| `hero-block.tsx` | `admin/src/components/blocks/hero-block.tsx` | EXISTS | Real images, full-bleed option |
| `body-text-block.tsx` | `admin/src/components/blocks/body-text-block.tsx` | EXISTS | Drop caps, magazine typography |
| `image-gallery-block.tsx` | `admin/src/components/blocks/image-gallery-block.tsx` | EXISTS | Carousel + masonry layout styles |
| `pull-quote-block.tsx` | `admin/src/components/blocks/pull-quote-block.tsx` | EXISTS | Decorative styling, larger font |
| `product-showcase-block.tsx` | `admin/src/components/blocks/product-showcase-block.tsx` | EXISTS | Real product images + links |
| `celeb-feature-block.tsx` | `admin/src/components/blocks/celeb-feature-block.tsx` | EXISTS | Real celebrity images, spotlight layout |
| `divider-block.tsx` | `admin/src/components/blocks/divider-block.tsx` | EXISTS | Ornament style variant implementation |
| `hashtag-bar-block.tsx` | `admin/src/components/blocks/hashtag-bar-block.tsx` | EXISTS | Interactive/pill styling |
| `credits-block.tsx` | `admin/src/components/blocks/credits-block.tsx` | EXISTS | Magazine footer styling, small caps |

**New frontend components:**

| Component | Purpose |
|-----------|---------|
| `preview-mode-toggle.tsx` | Mobile/tablet/desktop width switcher |
| `pipeline-timeline.tsx` | Node execution timeline (from Pillar 1) |

### Data Flow: No Changes Required

The data contract is already established and working:
- Python: `MagazineLayout` Pydantic model -> JSON -> Supabase `editorial_contents.layout_json`
- TypeScript: `MagazineLayout` interface mirrors Python model exactly
- Block discriminated union: `type` field dispatches to React components via `BLOCK_MAP`

**No API changes, no schema changes, no new data flow.** This is pure frontend enhancement work.

### Confidence Assessment

| Decision | Confidence | Rationale |
|----------|-----------|-----------|
| Block renderer already exists and works | HIGH | Verified by reading actual source code in all 10 block files |
| CSS-only enhancement approach | HIGH | Tailwind 4 + existing shadcn/ui, no new deps needed |
| Use `<img>` for external images (not next/image) | HIGH | External URLs from Supabase require `remotePatterns` config |
| No new data contract needed | HIGH | Python and TS types already match 1:1 (verified both files) |

---

## Pillar 3: E2E Setup

### What "E2E Setup" Means in This Context

The pipeline requires multiple external services to run end-to-end:
1. **Supabase REST API** -- for content CRUD (`editorial_contents` table)
2. **Supabase Postgres** -- for checkpointing (AsyncPostgresSaver, port 5432)
3. **Google AI** -- Gemini models for curation, editorial, review
4. **LangSmith** -- optional, for observability tracing

Currently, there is no validation that all services are reachable and properly configured before starting a pipeline run. A single missing env var (e.g., `GOOGLE_API_KEY`) causes a cryptic runtime error deep in the pipeline (at the first LLM call in `curation_node`).

### Recommended Architecture: Startup Validation + Health Checks + E2E Smoke Test

#### 1. Environment Validation Module

**File:** `src/editorial_ai/preflight.py`

```python
async def preflight_check() -> dict[str, dict]:
    """Validate all required services are reachable.
    Returns dict of service -> {status, message, latency_ms}.
    """
    results = {}
    results["supabase_rest"] = await _check_supabase_rest()
    results["postgres_checkpointer"] = await _check_postgres()
    results["google_ai"] = await _check_google_ai()
    if settings.langsmith_tracing:
        results["langsmith"] = await _check_langsmith()
    return results
```

Each check validates:
- **supabase_rest:** `SUPABASE_URL` + `SUPABASE_SERVICE_ROLE_KEY` set, can `SELECT 1` from `editorial_contents`
- **postgres_checkpointer:** `DATABASE_URL` set, can connect to Postgres pooler
- **google_ai:** `GOOGLE_API_KEY` (or Vertex AI credentials) set, can list models
- **langsmith:** `LANGSMITH_API_KEY` set, API reachable

#### 2. Integration with Existing FastAPI Lifespan

Modify `src/editorial_ai/api/app.py`:

```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    # NEW: preflight check before checkpointer setup
    from editorial_ai.preflight import preflight_check
    results = await preflight_check()
    app.state.preflight = results
    failed = [k for k, v in results.items() if v["status"] == "error"]
    if failed:
        logger.error("Preflight check failed for: %s", failed)
        # Don't crash server -- allow health endpoint to report status

    async with create_checkpointer() as checkpointer:
        await checkpointer.setup()
        app.state.checkpointer = checkpointer
        app.state.graph = build_graph(checkpointer=checkpointer)
        yield
```

#### 3. Enhanced Health Endpoint

```python
@app.get("/health")
async def health():
    preflight = getattr(app.state, "preflight", {})
    failed = [k for k, v in preflight.items() if v.get("status") == "error"]
    return {
        "status": "ok" if not failed else "degraded",
        "services": preflight,
    }
```

#### 4. Required Environment Variables (Complete Verified List)

Extracted from `src/editorial_ai/config.py` (Settings class):

| Variable | Required | Used By | Default |
|----------|----------|---------|---------|
| `GOOGLE_API_KEY` | YES (unless Vertex AI) | Gemini LLM calls (curation, editorial, review) | None |
| `GOOGLE_GENAI_USE_VERTEXAI` | NO | Switch to Vertex AI mode | None |
| `GOOGLE_CLOUD_PROJECT` | If Vertex AI | Vertex AI auth | None |
| `GOOGLE_CLOUD_LOCATION` | NO | Vertex AI region | "us-central1" |
| `SUPABASE_URL` | YES | Content CRUD, source queries | None |
| `SUPABASE_SERVICE_ROLE_KEY` | YES | Supabase auth (service role) | None |
| `DATABASE_URL` | YES | AsyncPostgresSaver (Postgres session pooler, port 5432) | None |
| `ADMIN_API_KEY` | YES | FastAPI API key authentication | None |
| `LANGSMITH_TRACING` | NO | Enable LangSmith tracing | False |
| `LANGSMITH_API_KEY` | If tracing | LangSmith auth | None |
| `LANGSMITH_PROJECT` | NO | LangSmith project name | "editorial-ai-worker" |
| `API_HOST` | NO | FastAPI bind host | "0.0.0.0" |
| `API_PORT` | NO | FastAPI bind port | 8000 |

Frontend (admin dashboard) env vars (from `admin/src/config.ts` and API routes):

| Variable | Required | Used By | Notes |
|----------|----------|---------|-------|
| `NEXT_PUBLIC_API_URL` | YES | Admin dashboard API calls | Base URL for FastAPI backend |
| `NEXT_PUBLIC_API_KEY` | YES | Admin dashboard auth | Matches `ADMIN_API_KEY` on backend |

#### 5. E2E Smoke Test Script

**File:** `scripts/e2e_smoke.py`

```python
"""End-to-end smoke test: trigger pipeline, wait for admin_gate, approve, verify published."""

async def run_e2e():
    # 1. Preflight check
    results = await preflight_check()
    assert all(v["status"] == "ok" for v in results.values())

    # 2. POST /api/pipeline/trigger with test keyword
    response = await client.post("/api/pipeline/trigger", json={"seed_keyword": "e2e-test", "category": "fashion"})
    thread_id = response.json()["thread_id"]

    # 3. Poll /api/contents?status=pending until content appears
    content = await poll_for_content(thread_id, timeout=120)

    # 4. POST /api/contents/{id}/approve
    await client.post(f"/api/contents/{content['id']}/approve", json={"feedback": "e2e auto-approve"})

    # 5. Verify status transitions
    final = await client.get(f"/api/contents/{content['id']}")
    assert final.json()["status"] == "published"

    # 6. Verify pipeline_node_runs has entries (if observability is implemented)
    runs = await client.get(f"/api/pipeline/runs/{thread_id}")
    assert len(runs.json()) >= 7  # all 7 nodes executed
```

#### 6. `.env.example` Template

Create `/.env.example` with all required variables documented:

```bash
# Required: Google AI
GOOGLE_API_KEY=your-google-api-key

# Required: Supabase
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_SERVICE_ROLE_KEY=your-service-role-key
DATABASE_URL=postgresql://user:pass@db.your-project.supabase.co:5432/postgres

# Required: API Authentication
ADMIN_API_KEY=your-admin-api-key

# Optional: LangSmith Observability
LANGSMITH_TRACING=false
LANGSMITH_API_KEY=
LANGSMITH_PROJECT=editorial-ai-worker
```

### Confidence Assessment

| Decision | Confidence | Rationale |
|----------|-----------|-----------|
| Preflight check pattern | HIGH | Standard pattern, no external deps, integrates with existing lifespan |
| Env var list completeness | HIGH | Extracted from actual config.py source (line by line) |
| E2E smoke test approach | MEDIUM | Depends on pipeline stability and LLM call timing |
| `.env.example` template | HIGH | Standard practice for onboarding |

---

## Complete Component Inventory (New vs Modified)

### New Components

| Component | Layer | File Path | Purpose |
|-----------|-------|-----------|---------|
| `observability.py` | Backend | `src/editorial_ai/observability.py` | `node_wrapper` decorator + save logic |
| `preflight.py` | Backend | `src/editorial_ai/preflight.py` | Service health validation at startup |
| `pipeline_node_runs` | Database | Supabase SQL migration | Execution log table |
| `pipeline-timeline.tsx` | Frontend | `admin/src/components/pipeline-timeline.tsx` | Node execution timeline visualization |
| `preview-mode-toggle.tsx` | Frontend | `admin/src/components/preview-mode-toggle.tsx` | Device width switcher for preview |
| `e2e_smoke.py` | Script | `scripts/e2e_smoke.py` | End-to-end validation script |
| `.env.example` | Config | `.env.example` | Environment variable documentation |

### Modified Components

| Component | File Path | Change Summary |
|-----------|-----------|----------------|
| `graph.py` | `src/editorial_ai/graph.py` | Wrap nodes with `node_wrapper()` in `build_graph()` |
| `app.py` | `src/editorial_ai/api/app.py` | Add preflight check to lifespan, enhance `/health` |
| `pipeline.py` (routes) | `src/editorial_ai/api/routes/pipeline.py` | Add `/runs/{thread_id}` and `/runs/recent` endpoints |
| `hero-block.tsx` | `admin/src/components/blocks/hero-block.tsx` | Real image rendering with fallback |
| `product-showcase-block.tsx` | `admin/src/components/blocks/product-showcase-block.tsx` | Real product images |
| `celeb-feature-block.tsx` | `admin/src/components/blocks/celeb-feature-block.tsx` | Real celebrity images |
| `image-gallery-block.tsx` | `admin/src/components/blocks/image-gallery-block.tsx` | Carousel + masonry layout implementations |
| `body-text-block.tsx` | `admin/src/components/blocks/body-text-block.tsx` | Magazine typography (leading, drop cap) |
| `pull-quote-block.tsx` | `admin/src/components/blocks/pull-quote-block.tsx` | Decorative styling (border, large font) |
| `divider-block.tsx` | `admin/src/components/blocks/divider-block.tsx` | Ornament style variant |
| `hashtag-bar-block.tsx` | `admin/src/components/blocks/hashtag-bar-block.tsx` | Pill/tag styling |
| `credits-block.tsx` | `admin/src/components/blocks/credits-block.tsx` | Magazine footer styling |
| Content detail page | `admin/src/app/contents/[id]/page.tsx` | Add timeline + preview toggle sections |

---

## Data Flow Changes

### Before (v1.0)

```
Pipeline Node -> State Update -> Supabase (editorial_contents only)
Admin Dashboard -> GET /api/contents -> Render blocks from layout_json (placeholder images)
```

### After (v1.1)

```
Pipeline Node -> node_wrapper() -> State Update + pipeline_node_runs INSERT (fire-and-forget)
                                         |
Admin Dashboard -> GET /api/contents/{id}       -> Render blocks with real images + magazine CSS
               -> GET /api/pipeline/runs/{tid}  -> Render execution timeline
               -> GET /health                   -> Show service status

Startup -> preflight_check() -> /health reports service status per dependency
```

The only new data flow is `pipeline_node_runs` writes from the `node_wrapper`. Everything else is enhancement of existing flows.

---

## Suggested Build Order

**Phase order is driven by dependencies and testing ability:**

### Phase 1: E2E Setup (Foundation)
Without validated env vars and health checks, you cannot reliably test anything else. Also serves as documentation for onboarding.
- `.env.example` file
- `preflight.py` module
- Enhanced `/health` endpoint
- Basic `e2e_smoke.py` script (no observability assertions yet)

### Phase 2: Pipeline Observability (Backend)
The `node_wrapper` decorator + Supabase table + API endpoints. Pure backend work that can be validated via API calls alone.
- `pipeline_node_runs` Supabase table creation
- `observability.py` module
- Wrap nodes in `graph.py`
- `/api/pipeline/runs` endpoints

### Phase 3: Magazine Renderer Enhancement (Frontend, parallelizable with Phase 2)
Pure frontend CSS/component work. No backend dependency. Can be done in parallel with Phase 2 after the E2E foundation is in place.
- Image rendering for hero, product, celeb blocks
- Gallery carousel + masonry layouts
- Typography and spacing improvements
- Divider ornament variant

### Phase 4: Dashboard Integration (Frontend, depends on Phase 2 + 3)
Combines observability API data with enhanced renderer on the content detail page.
- `pipeline-timeline.tsx` component
- `preview-mode-toggle.tsx` component
- Integration on content detail page
- Update E2E smoke test with observability assertions

### Dependency Graph

```
Phase 1: E2E Setup (preflight + env validation + .env.example)
    |
    +---------------------------+
    |                           |
    v                           v
Phase 2: Observability     Phase 3: Magazine Renderer
(node_wrapper + table +    (block CSS enhancements +
 API endpoints)             real images)
    |                           |
    +---------------------------+
    |
    v
Phase 4: Dashboard Integration
(timeline + preview toggle on detail page)
```

---

## Anti-Patterns to Avoid

### Anti-Pattern 1: Storing Observability Data in Pipeline State

**What:** Adding `node_timings: list[dict]` to `EditorialPipelineState`.
**Why bad:** Violates the lean state principle (state.py comment: "Lean: ID/references only, no payloads"). State is checkpointed to Postgres on every node transition. Observability data bloats checkpoints and couples observability to pipeline correctness.
**Instead:** Write to separate `pipeline_node_runs` table via `node_wrapper`, completely decoupled from state.

### Anti-Pattern 2: Blocking Pipeline on Observability Writes

**What:** Awaiting `save_node_run(...)` in the critical path without error handling.
**Why bad:** If Supabase is slow or temporarily down, observability failure kills the actual content pipeline.
**Instead:** Fire-and-forget pattern with `try/except pass` in `node_wrapper`'s `finally` block. Observability must never break the pipeline.

### Anti-Pattern 3: Building Custom Tracing When LangSmith is Available

**What:** Building per-LLM-call tracing, token counting, input/output logging from scratch.
**Why bad:** LangSmith already does this automatically with `LANGSMITH_TRACING=true`. The project already has the dependency (`langsmith>=0.7.5`) and config.
**Instead:** Use LangSmith for deep developer tracing. Use `pipeline_node_runs` only for admin-facing summary metrics (node name, duration, success/error).

### Anti-Pattern 4: Adding Frontend-Only Props to Block Components

**What:** Adding `variant`, `theme`, `size` props to block components that don't exist in the Python `MagazineLayout` model.
**Why bad:** Creates a divergence between the Python Pydantic model and TypeScript types. The 1:1 type parity between `layout.py` and `types.ts` is a valuable contract.
**Instead:** Use CSS-only styling via Tailwind classes. The block data shape should remain identical to the Python model.

### Anti-Pattern 5: Using next/image for External URLs Without Configuration

**What:** Using `<Image>` from `next/image` for URLs coming from Supabase or external sources.
**Why bad:** Next.js requires `remotePatterns` in `next.config.ts` for external image domains. The editorial pipeline can reference images from arbitrary domains (social media, product sites, etc.).
**Instead:** Use standard `<img>` tags for external URLs. Only use `next/image` for static assets or known, configured domains.

---

## Sources

- [LangSmith: Trace LangGraph Applications](https://docs.langchain.com/langsmith/trace-with-langgraph) -- HIGH confidence, verified auto-tracing via env vars, per-node trace capture
- [LangSmith Observability for LangGraph](https://docs.langchain.com/oss/python/langgraph/observability) -- HIGH confidence, LangGraph-specific observability integration
- [LangChain Callbacks Concepts](https://python.langchain.com/docs/concepts/callbacks/) -- HIGH confidence, custom callback event dispatch for @traceable
- [LangSmith for Agent Observability (Medium, Jan 2026)](https://ravjot03.medium.com/langsmith-for-agent-observability-tracing-langgraph-tool-calling-end-to-end-2a97d0024dfb) -- MEDIUM confidence, practical example of LangSmith + LangGraph tracing
- [Dynamic Layouts in Next.js 15 with CMS Blocks (Medium)](https://medium.com/@sureshdotariya/dynamic-layouts-in-next-js-15-contentful-cms-empowering-non-devs-with-cms-blocks-dca480afef37) -- MEDIUM confidence, block-based rendering patterns for Next.js 15
- [Render Block Components in Next.js (DEV Community)](https://dev.to/aswanth_raveendranek_a2a/render-block-component-in-next-js-and-headless-cms-24f3) -- MEDIUM confidence, block renderer dispatch pattern
- Codebase analysis: `config.py` (LangSmith settings lines 38-44), `graph.py` (node registration + override pattern), `block-renderer.tsx` (existing 10-block BLOCK_MAP renderer), `types.ts` (1:1 Python-TypeScript type parity), `layout.py` (10 Pydantic block models with discriminated union)
