# Technology Stack — v1.1 Additions

**Project:** Editorial AI Worker
**Milestone:** v1.1 Pipeline Observability + Dynamic Magazine Renderer + E2E Setup
**Researched:** 2026-02-26
**Overall Confidence:** HIGH

> This document covers ONLY new stack additions for v1.1. The validated v1.0 stack (LangGraph, Gemini, Supabase, FastAPI, Next.js 15) is unchanged.

---

## 1. Pipeline Observability (Per-Node Token/Latency/Prompt Logging)

### Recommended Approach: Custom Callback + Supabase Storage

**Do NOT add LangSmith as a runtime dependency for this.** LangSmith is already configured in the codebase (config.py has LANGSMITH_TRACING settings) and works via environment variables — it requires zero code changes. But the v1.1 requirement is to **store per-node logs in Supabase and display them in the Admin Dashboard**, not to rely on an external SaaS dashboard.

### Strategy: `langchain_core.callbacks` + Custom DB Persistence

| Technology | Version | Purpose | Why | Confidence |
|------------|---------|---------|-----|------------|
| `langchain-core` (already installed) | 1.2.14 (current) | `UsageMetadataCallbackHandler`, `BaseCallbackHandler` | Built-in callback system tracks `AIMessage.usage_metadata` with input/output/total tokens per LLM call. No new dependency needed. | HIGH |
| Supabase `pipeline_node_logs` table | (new migration) | Persist per-node execution metrics | Co-located with existing `editorial_contents` table. JOIN on `thread_id` for Admin detail page queries. | HIGH |

**What NOT to add:**

| Rejected Option | Why Not |
|-----------------|---------|
| Langfuse | Over-engineered for this use case. We need per-node metrics in OUR Admin UI, not a separate observability dashboard. Adds infrastructure (self-hosted) or SaaS cost. |
| OpenTelemetry / Jaeger | Infrastructure-level tracing. Doesn't understand LLM-specific metrics (tokens, prompt content). Wrong abstraction layer. |
| MLflow | Heavy ML experiment tracking platform. Massive dependency for what is essentially "log 6 rows per pipeline run." |
| Custom `time.time()` wrappers | Fragile. Doesn't capture token usage from LLM responses. The callback system already does this properly. |

### Implementation Pattern

The existing node functions (curation_node, editorial_node, etc.) call services that call LLMs. Two complementary approaches:

**Approach A: Per-node callback handler (recommended)**

Create a custom `AsyncCallbackHandler` subclass that:
1. Captures `on_llm_start` — records start time, prompt content
2. Captures `on_llm_end` — records end time, `response.usage_metadata` (input_tokens, output_tokens, total_tokens)
3. Tags each entry with the current node name

Pass it via LangGraph's `config={"callbacks": [handler]}` at graph invocation time. LangGraph propagates callbacks to all nodes automatically.

```python
from langchain_core.callbacks import AsyncCallbackHandler
from langchain_core.outputs import LLMResult
import time
from dataclasses import dataclass, field

@dataclass
class NodeExecutionLog:
    node_name: str
    started_at: float
    ended_at: float | None = None
    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0
    prompt_preview: str = ""  # First 500 chars of prompt
    error: str | None = None

class PipelineObservabilityHandler(AsyncCallbackHandler):
    logs: list[NodeExecutionLog] = field(default_factory=list)
    # Implementation captures on_llm_start/on_llm_end per node
```

**Approach B: Node wrapper decorator (complementary)**

Wrap each node function to capture wall-clock time and input/output state size. This captures non-LLM node timing (e.g., enrich node does DB queries, not LLM calls).

```python
def observed_node(node_fn):
    async def wrapper(state):
        start = time.monotonic()
        result = await node_fn(state)
        elapsed = time.monotonic() - start
        # Store timing in a sideband channel
        return result
    return wrapper
```

**Combined:** Callback handler captures LLM-specific metrics. Wrapper captures wall-clock time for ALL nodes (including non-LLM nodes like source, enrich, publish).

### Database Schema Addition

```sql
-- New migration: 002_pipeline_node_logs.sql
CREATE TABLE pipeline_node_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    thread_id TEXT NOT NULL REFERENCES editorial_contents(thread_id),
    node_name TEXT NOT NULL,
    started_at TIMESTAMPTZ NOT NULL,
    ended_at TIMESTAMPTZ,
    duration_ms INTEGER,
    input_tokens INTEGER DEFAULT 0,
    output_tokens INTEGER DEFAULT 0,
    total_tokens INTEGER DEFAULT 0,
    prompt_preview TEXT,          -- First 500 chars (avoid storing full prompts for cost)
    output_preview TEXT,          -- First 500 chars of LLM response
    input_state_keys TEXT[],      -- Which state keys were read
    error TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_pipeline_node_logs_thread ON pipeline_node_logs(thread_id);
CREATE INDEX idx_pipeline_node_logs_node ON pipeline_node_logs(node_name);
```

### API Endpoint Addition

```
GET /api/contents/{id}/logs  ->  List[NodeExecutionLog]
```

Returns per-node logs for the Admin detail page. Simple Supabase query on `thread_id`.

---

## 2. Dynamic Magazine Layout Renderer (Admin Dashboard)

### Current State

The Admin dashboard ALREADY has a working `BlockRenderer` component with 10 block type components:
- `hero-block.tsx`, `headline-block.tsx`, `body-text-block.tsx`, `image-gallery-block.tsx`
- `pull-quote-block.tsx`, `product-showcase-block.tsx`, `celeb-feature-block.tsx`
- `divider-block.tsx`, `hashtag-bar-block.tsx`, `credits-block.tsx`

These are functional but visually minimal (placeholder images, basic typography). The v1.1 goal is to make them **visually rich** — magazine-quality rendering.

### Recommended Additions

| Technology | Version | Purpose | Why | Confidence |
|------------|---------|---------|-----|------------|
| `motion` | `^12.x` | Scroll reveal, entrance animations | Renamed from `framer-motion`. The standard React animation library. v12+ supports React 19. Enables magazine-feel scroll reveals, image fade-ins, parallax-lite effects. | HIGH |
| `next/image` (built-in) | (Next.js 15) | Optimized image rendering | Already available in Next.js. Use for hero images, gallery images, product photos. Automatic lazy loading, blur placeholders, responsive sizing. Zero new dependency. | HIGH |
| `@next/font` (built-in) | (Next.js 15) | Editorial typography | Built into Next.js. Load serif/display fonts (Playfair Display, etc.) for magazine headlines. Zero new dependency. | HIGH |
| Tailwind CSS (already installed) | v4 | Rich styling | Already in the project. v4 with modern CSS features (container queries, has: selector) is sufficient for magazine layouts. No CSS-in-JS needed. | HIGH |

**What NOT to add:**

| Rejected Option | Why Not |
|-----------------|---------|
| Three.js / React Three Fiber | Out of scope. PROJECT.md explicitly states "프론트엔드 매거진 뷰어 (threejs/gsap) — decoded-app 레포에서 별도 구현". This Admin renderer is for preview/approval, not the consumer-facing viewer. |
| GSAP | Same as above — consumer-facing animations belong in decoded-app. Motion is lighter and sufficient for Admin preview. |
| Styled Components / Emotion | Project uses Tailwind v4. Adding CSS-in-JS is contradictory and adds bundle size. |
| MDX / Rich text editor | Layout JSON is the contract. We render blocks, not editable rich text. |
| Contentful / Strapi SDK | No CMS integration needed. Data comes from our own Supabase. |

### Implementation Strategy

The block renderer architecture is already correct (discriminated union of block types -> component map). The work is purely visual enhancement:

1. **Hero Block**: Full-bleed image with `next/image`, gradient overlay, animated text reveal via `motion`
2. **Image Gallery**: Masonry/carousel support with real images (not "Product Photo" placeholders), lightbox on click
3. **Product Showcase**: Card grid with actual product images, hover effects
4. **Pull Quote**: Large serif typography, decorative quotation marks, subtle entrance animation
5. **Body Text**: Drop caps, proper leading/tracking, serif font for body copy
6. **Celeb Feature**: Portrait image with name overlay, card-based layout

### Font Strategy

```typescript
// app/layout.tsx — add editorial fonts
import { Playfair_Display, Noto_Sans_KR } from 'next/font/google'

const playfair = Playfair_Display({
  subsets: ['latin'],
  variable: '--font-editorial-display',
})

const notoSansKr = Noto_Sans_KR({
  subsets: ['latin'],
  variable: '--font-editorial-body',
})
```

Korean content needs `Noto Sans KR` (or `Noto Serif KR` for body). English headlines use a display serif.

### Install Command

```bash
cd admin && pnpm add motion
```

That is the ONLY new npm dependency for the renderer. Everything else is built-in (next/image, next/font, Tailwind v4).

---

## 3. E2E Environment Setup & Execution Validation

### What This Means

The v1.0 pipeline was built and tested with **mocked services** (stub nodes in tests, no real Gemini calls, no real Supabase data). v1.1 needs to run the FULL pipeline end-to-end with:
- Real Gemini API calls (GOOGLE_API_KEY)
- Real Supabase connection (SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)
- Real Postgres checkpointer (DATABASE_URL)
- Real data flowing through all 7 nodes

### No New Dependencies Required

All infrastructure dependencies are already in `pyproject.toml`. The E2E setup is about:

| Task | Technology | Notes |
|------|-----------|-------|
| Environment validation script | Python + existing config.py | Script that validates all env vars are set and connections work |
| Integration test runner | pytest with `-m integration` marker | Already configured in `pyproject.toml` (`addopts = "-m 'not integration'"`) |
| Supabase seed data | SQL migration or Python script | Ensure celebs/products exist in DB for source/enrich nodes |
| E2E test | pytest + real graph invocation | Single test that runs `build_graph()` with real checkpointer and real LLM calls |

### E2E Validation Script Pattern

```python
# scripts/validate_env.py
"""Validate all environment variables and connections for E2E execution."""

async def validate():
    # 1. Check required env vars exist
    # 2. Test Supabase REST API connection
    # 3. Test Postgres direct connection (checkpointer)
    # 4. Test Gemini API with a minimal call
    # 5. Verify seed data exists (celebs table has rows, products table has rows)
    print("All checks passed. Ready for E2E pipeline run.")
```

### Integration Test Marker

Already configured. Run with:
```bash
uv run pytest -m integration
```

### What NOT to add for E2E:

| Rejected Option | Why Not |
|-----------------|---------|
| Docker Compose | Supabase is a managed service. No local DB setup needed. The only local dependency is Python + env vars. |
| Testcontainers | Same reason. We test against real Supabase, not containerized Postgres. |
| Playwright / Cypress | E2E here means pipeline execution, not browser testing. Admin UI testing is a separate concern. |
| CI/CD pipeline (GitHub Actions) | Out of v1.1 scope. E2E validation is local-first. CI can come later. |

---

## Summary: What Changes in pyproject.toml

### Python Dependencies: NOTHING NEW

All required Python packages are already installed:
- `langchain-core` 1.2.14 (has `UsageMetadataCallbackHandler`)
- `langgraph` 1.0.9 (has callback propagation)
- `supabase` (for storing logs)
- `fastapi` (for serving logs API)
- `pytest` with integration markers (for E2E tests)

### Admin Dashboard (package.json): ONE NEW DEPENDENCY

```bash
cd admin && pnpm add motion  # ~50KB gzipped, React 19 compatible
```

### Database: ONE NEW MIGRATION

```
supabase/migrations/002_pipeline_node_logs.sql
```

### New Files to Create

| File | Purpose |
|------|---------|
| `src/editorial_ai/observability.py` | Custom callback handler + node wrapper |
| `src/editorial_ai/services/log_service.py` | CRUD for pipeline_node_logs table |
| `src/editorial_ai/api/routes/logs.py` | GET /api/contents/{id}/logs endpoint |
| `supabase/migrations/002_pipeline_node_logs.sql` | Node logs table |
| `scripts/validate_env.py` | E2E environment validation |
| `tests/test_e2e_pipeline.py` | Full pipeline integration test |
| Enhanced block components in `admin/src/components/blocks/*.tsx` | Visual upgrades |
| `admin/src/app/contents/[id]/logs-panel.tsx` | Pipeline logs display component |

---

## Confidence Assessment

| Area | Level | Reason |
|------|-------|--------|
| Observability approach | HIGH | `langchain_core.callbacks` is the documented, standard way. `UsageMetadataCallbackHandler` verified in installed version 1.2.14. No external dependency needed. |
| Database schema | HIGH | Simple relational table with FK to existing `editorial_contents`. Standard Supabase pattern. |
| Magazine renderer | HIGH | Block renderer architecture already exists. `motion` (framer-motion rebrand) is the de facto React animation library. v12 confirmed React 19 compatible. |
| E2E setup | HIGH | All infrastructure already provisioned. This is configuration and scripting, not new technology. |

---

## Sources

- [LangChain: How to track token usage in ChatModels](https://python.langchain.com/docs/how_to/chat_token_usage_tracking/) — UsageMetadataCallbackHandler docs
- [LangChain: UsageMetadataCallbackHandler API Reference](https://python.langchain.com/api_reference/core/callbacks/langchain_core.callbacks.usage.UsageMetadataCallbackHandler.html)
- [LangChain: get_usage_metadata_callback context manager](https://python.langchain.com/api_reference/core/callbacks/langchain_core.callbacks.usage.get_usage_metadata_callback.html)
- [LangChain Forum: Token usage from LangGraph](https://forum.langchain.com/t/how-to-obtain-token-usage-from-langgraph/1727) — Community patterns
- [LangChain Changelog: Universal token counting callback](https://changelog.langchain.com/announcements/universal-token-counting-callback-for-langchain-python)
- [Motion (formerly Framer Motion)](https://motion.dev) — React animation library
- [Motion React Upgrade Guide](https://motion.dev/docs/react-upgrade-guide) — framer-motion to motion migration
- [Langfuse LangGraph Integration](https://langfuse.com/guides/cookbook/example_langgraph_agents) — Reviewed and rejected for this use case
- [Directus: Rendering Dynamic Blocks Using Next.js](https://directus.io/docs/tutorials/getting-started/rendering-dynamic-blocks-using-next) — Block renderer pattern reference
