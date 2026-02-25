# Feature Landscape

**Domain:** Pipeline Observability + Dynamic Magazine Renderer + E2E Setup for Editorial AI Pipeline
**Researched:** 2026-02-26
**Milestone:** v1.1 (builds on shipped v1.0)
**Overall confidence:** HIGH -- Based on detailed codebase analysis of all node, service, block component, and API files, cross-referenced with ecosystem research.

---

## Context: What v1.0 Already Shipped

Before detailing v1.1 features, here is what exists and works:

- LangGraph 7-node pipeline: curation -> source -> editorial -> enrich -> review -> admin_gate -> publish
- 10 block-type React components in `admin/src/components/blocks/` (structurally complete, visually placeholder)
- `BlockRenderer` with discriminated union dispatch (`BLOCK_MAP` registry)
- FastAPI admin API with CRUD + pipeline trigger endpoint
- Admin Dashboard (Next.js 15): content list, detail page with JSON panel + block preview, approve/reject flow
- Supabase `editorial_contents` table with status workflow
- Postgres checkpointer for LangGraph state persistence
- LangSmith tracing as opt-in (`LANGSMITH_TRACING` env var)
- Demo mode in admin frontend (`demo-data.ts`)

---

## Table Stakes

Features the user explicitly expects for v1.1. Missing = milestone goal is not met.

### 1. E2E Execution Environment Setup

| Feature | Why Expected | Complexity | Dependencies | Notes |
|---------|--------------|------------|--------------|-------|
| **Environment variable validation at startup** | Pipeline requires GOOGLE_API_KEY, SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY, DATABASE_URL. Current `config.py` makes all fields `str | None` with no startup checks. First Gemini call fails cryptically without API key | Low | `config.py` Settings model | Add a `validate_required()` method or Pydantic `@model_validator` that fails fast with clear messages |
| **Supabase connection + table health check** | Pipeline reads celebs/products/posts and writes editorial_contents. Missing tables produce cryptic 400/404 from Supabase REST API | Low | `supabase_client.py` | Health-check endpoint (`GET /health`) that verifies connectivity and table existence |
| **Checkpointer connection validation** | `AsyncPostgresSaver` requires working DATABASE_URL with `sslmode=require` for Supabase. This is the most common failure point for first-time setup | Medium | `checkpointer.py` | Supabase connection pooler (port 5432 session mode) has specific SSL and prepared statement requirements |
| **Pipeline trigger from Admin UI** | Pipeline trigger exists as API (`POST /pipeline/trigger`) but Admin UI has no button for it. User must use curl/Postman for first run | Low | Existing trigger endpoint | "New Content" button + keyword input form on Admin contents page |
| **Seed data for first run** | Source node queries Supabase for celebs/products/posts. Empty tables mean enrichment returns nothing, editorial has no real data | Low | Supabase tables exist | SQL seed script or API-based seeder with sample celebs/products |
| **`curation_input` field mapping verification** | Pipeline trigger sends `seed_keyword` but curation node reads `curation_input.keyword` vs `curation_input.seed_keyword` -- potential mismatch needs verification and fix | Low | `pipeline.py` trigger + `curation.py` node | Must trace exact field names end-to-end |

### 2. Pipeline Observability

| Feature | Why Expected | Complexity | Dependencies | Notes |
|---------|--------------|------------|--------------|-------|
| **Per-node execution time tracking** | Without timing data, impossible to identify bottlenecks across 7 nodes. Editorial node alone does 3 Gemini calls (content + image + vision) | Low | Python `time.perf_counter()` wrapping | Measure wall-clock time for each node |
| **Per-node token usage collection** | LLM costs are the primary operational expense. 4 of 7 nodes call Gemini: curation, editorial (3 calls), review, and enrich (optional) | Medium | google-genai `response.usage_metadata` exposes `prompt_token_count`, `candidates_token_count`, `total_token_count` | Services use native google-genai SDK, NOT langchain. LangChain callbacks do NOT apply to these calls |
| **Prompt text capture per node** | "What prompt was sent?" is the first debugging question. Prompts are built by `build_*_prompt()` functions in `prompts/` | Low | Capture string before `client.aio.models.generate_content()` call | Store alongside node log entry |
| **Per-node input data snapshot** | "What data entered this node?" is the second debugging question | Low | State keys read by each node are known and fixed | Store trimmed version (first 500 chars of large fields) |
| **Pipeline run log persistence (Supabase)** | Logs must survive restarts; Admin reads from DB | Medium | New `pipeline_run_logs` table | JSONB column for node-level detail array, foreign key to `editorial_contents.thread_id` |
| **Admin detail page: pipeline log panel** | The stated goal: "see detailed per-node logs in Admin content detail page" | Medium | Pipeline log API endpoint + React component | Tab or accordion showing node-by-node timeline with expandable details |

### 3. Dynamic Magazine Renderer

| Feature | Why Expected | Complexity | Dependencies | Notes |
|---------|--------------|------------|--------------|-------|
| **Upgrade block components from placeholders to real rendering** | Current blocks show placeholder text ("Hero Image", "Product Photo", "Photo") instead of actual images. This defeats the purpose of a magazine preview | Medium | All 10 block components in `admin/src/components/blocks/` | `hero-block.tsx` shows gray div; must render `block.image_url` via `<img>` or Next `<Image>`. Same for product, celeb, image gallery blocks |
| **Image loading with fallbacks** | `image_url` may be empty string (default template uses `""`), broken URL, or slow. Must handle gracefully without breaking the page | Low | None | Show placeholder gradient/skeleton when URL is empty; onError handler for broken URLs |
| **Magazine-quality typography** | Body text is plain gray paragraphs. Magazine editorial expects varied font families (serif for body, sans-serif for headlines), proper line-height, drop caps, etc. | Low-Med | Google Fonts or local font files + Tailwind config | Pull quote already uses Georgia; extend to a cohesive typographic system |
| **Block-level error boundaries** | If one block has malformed data (e.g., undefined nested field), the entire magazine preview crashes | Low | React Error Boundary wrapping each `<Component>` in `BlockRenderer` | Currently no error boundaries exist |
| **Responsive layout verification** | Magazine content viewed on various screen sizes must not break | Low | Existing Tailwind responsive utilities | Current grid layouts (product 2-3 cols, celeb 2-3 cols) need breakpoint testing |

---

## Differentiators

Features that add significant value beyond the stated goals. Not required but recommended based on low effort-to-value ratio.

| Feature | Value Proposition | Complexity | Dependencies | Notes |
|---------|-------------------|------------|--------------|-------|
| **Token cost estimation display** | Show "This run cost ~$0.03" in Admin log panel. Converts abstract token counts to real money | Low | Gemini 2.5 Flash pricing table (static: $0.15/1M input, $0.60/1M output) | Simple multiplication. Huge value for cost awareness |
| **Side-by-side JSON + rendered view** | Toggle or split-view between raw JSON and rendered magazine on detail page | Low | Already have `JsonPanel` + `BlockRenderer`. Need CSS layout change | Currently stacked vertically. Side-by-side is more useful for debugging |
| **Pipeline progress status in list view** | Show which node the pipeline is currently at (curating/sourcing/drafting/reviewing/awaiting) in the content list table | Low | `pipeline_status` field already exists in state and presumably stored | Adds visibility without needing to click into detail page |
| **Magazine theme system (CSS variables)** | Multiple visual themes (dark editorial, bright lifestyle, minimal) via CSS variables on the preview container | Medium | CSS custom properties + theme selector dropdown | Differentiates from "render blocks in order" approach. But defer to post-v1.1 |
| **Real-time pipeline progress (SSE)** | Show live "Curating... Sourcing... Drafting..." instead of waiting 30-120s with a spinner | High | Server-Sent Events from FastAPI + LangGraph `astream_events()` | Replaces fire-and-wait pattern. Valuable but significant complexity |
| **Prompt playground in Admin** | View and edit prompts per node, test with different parameters | High | Prompt storage/versioning, sandbox execution | Defer: do prompt engineering in code for now |
| **Pipeline comparison view** | Compare two runs side-by-side (A/B testing prompts or models) | High | Multiple run storage, diff view component | Defer: need multiple successful runs first |
| **Print/export magazine as PDF** | One-click PDF export of the rendered magazine layout | Medium | `html2canvas` or Puppeteer SSR | Nice for stakeholder reviews but not urgent |

---

## Anti-Features

Features to explicitly NOT build. Common mistakes in this domain.

| Anti-Feature | Why Avoid | What to Do Instead |
|--------------|-----------|-------------------|
| **LangSmith/Langfuse as mandatory dependency** | Adds external SaaS dependency, cost, and complexity. For v1.1 with 1-2 users (dev team), custom lightweight logging is sufficient and gives full control over data shape | Build custom per-node logging that writes to Supabase JSONB. Keep `LANGSMITH_TRACING` as opt-in supplementary tool (already configured) |
| **OpenTelemetry/Jaeger full observability stack** | Massive infrastructure overhead for 7 nodes and 1-2 concurrent runs. Overkill for this scale | Structured logs in Supabase JSONB. Query via API. Display in Admin UI. Add OTel later if pipeline scales to hundreds of concurrent runs |
| **Full CMS visual editor (drag-drop blocks)** | The pipeline generates layout; admin reviews. A visual editor implies manual content creation which contradicts the core value (AI generates everything) | Keep rendered preview read-only. Admin approves/rejects, does not rearrange blocks |
| **Custom rendering engine (Canvas/WebGL/Three.js)** | Over-engineering for an admin preview. The consumer-facing renderer lives in `decoded-app` with Three.js/GSAP (explicitly out of scope) | Standard React + Tailwind components with magazine-quality CSS |
| **Block-level inline editing in preview** | Tempting to let admins tweak text in rendered view. Creates nightmare of two-way sync between JSON and DOM | Keep renderer as pure display. If editing needed later, provide structured form that modifies the JSON directly |
| **Automated cost alerting/budgets** | Premature for v1.1. Pipeline runs are manual (admin-triggered), not scheduled at scale | Display cost per-run in UI. Manual monitoring suffices |
| **Real-time collaborative editing** | Not relevant for single-admin approval flow | Lock content during review if needed |
| **Complex retry/resume UI per node** | Allowing admin to re-run individual nodes requires deep checkpoint manipulation and creates confusing UX | Full pipeline re-trigger with feedback. LangGraph handles internal retries (review loop) |

---

## Feature Dependencies

```
Phase 1: E2E Environment Setup
  |-- Env var validation at startup
  |-- Supabase health check
  |-- Checkpointer connection validation
  |-- Seed data script
  |-- Pipeline trigger button in Admin
  |-- curation_input field mapping fix
  |
  v
Phase 2: Pipeline Observability
  |-- Node instrumentation middleware (timing + tokens + prompts)
  |     |
  |     v
  |-- pipeline_run_logs Supabase table (migration)
  |     |
  |     v
  |-- Pipeline log API endpoint (GET /api/contents/{id}/logs)
  |     |
  |     v
  |-- Admin pipeline log panel (React accordion/timeline)
  |-- Token cost estimation (uses token data from middleware)
  |
  v
Phase 3: Magazine Renderer Upgrade
  |-- Upgrade 4 image-bearing blocks (hero, product, celeb, gallery)
  |-- Image fallback/loading states
  |-- Typography system (fonts, spacing, drop caps)
  |-- Block-level error boundaries
  |-- Responsive verification
  |-- Side-by-side JSON + rendered view
```

**Critical dependency:** E2E setup MUST come first. You cannot test observability without a working pipeline producing real data. You cannot test the magazine renderer without real Layout JSON from a successful pipeline run.

**Secondary dependency:** Observability middleware should be built before the Admin log panel, since the panel needs data to display. However, renderer upgrade is independent of observability and can proceed in parallel once real Layout JSON data exists.

---

## MVP Recommendation

### Phase 1: E2E Execution (prerequisite for everything)
1. Environment variable validation with fail-fast startup
2. Supabase connection + table health check endpoint
3. Checkpointer (DATABASE_URL) connection validation with SSL guidance
4. `curation_input` field mapping verification and fix
5. Pipeline trigger button + keyword input in Admin UI
6. Seed data SQL script for celebs/products/posts

### Phase 2: Pipeline Observability
1. Per-node instrumentation middleware (timing + token usage + prompt capture)
2. `pipeline_run_logs` Supabase table + migration SQL
3. Pipeline log API endpoint (`GET /api/contents/{id}/logs`)
4. Admin detail page: pipeline log panel (accordion/timeline)
5. Token cost estimation display (low-effort differentiator)

### Phase 3: Magazine Renderer Upgrade
1. Upgrade hero, product showcase, celeb feature, image gallery blocks to render real images
2. Image fallback/loading states for empty/broken URLs
3. Magazine typography system (Google Fonts, line-height, drop caps)
4. Block-level error boundaries in BlockRenderer
5. Responsive breakpoint verification
6. Side-by-side JSON + rendered view layout (low-effort differentiator)

### Defer to post-v1.1:
- **Real-time pipeline progress (SSE):** High complexity; runs take <2 min, acceptable wait
- **Prompt playground:** Valuable but significant scope; iterate prompts in code
- **Pipeline comparison view:** Need accumulated runs first
- **Magazine theme variants:** Get one solid theme working first
- **PDF export:** Screenshot suffices for stakeholder reviews
- **Node-level re-run from Admin:** Complex checkpoint manipulation

---

## Technical Notes

### Observability: Why Custom Logging, Not LangSmith/Langfuse

The codebase uses the **native google-genai SDK** (not langchain-google-genai) for all main LLM calls:

```python
# From editorial_service.py, curation_service.py, review_service.py:
response = await self.client.aio.models.generate_content(
    model=self.content_model,
    contents=prompt,
    config=types.GenerateContentConfig(...)
)
```

This means:
- **LangChain callback handlers DO NOT intercept these calls.** The `CallbackHandler` pattern (Langfuse, LangSmith callbacks) only instruments LangChain `ChatModel.invoke()` calls
- The `create_llm()` factory in `llm.py` creates a `ChatGoogleGenerativeAI` (LangChain wrapper) but it appears **unused by the main pipeline nodes**
- **Token usage IS available** on google-genai responses via `response.usage_metadata` containing `prompt_token_count`, `candidates_token_count`, `total_token_count`
- LangSmith tracing (already configured) captures the LangGraph graph-level execution but NOT the internal google-genai API calls within nodes

Therefore, custom per-node instrumentation at the service layer is the correct approach. The middleware should:
1. Record `time.perf_counter()` before/after each node
2. Have services return token usage metadata alongside their results
3. Capture the prompt string before sending to Gemini
4. Write structured log entries to Supabase

### Magazine Renderer: Current State vs. Target

**Current state** (from codebase analysis):

| Block | Current Rendering | Gap |
|-------|------------------|-----|
| `hero-block.tsx` | Gray box with "Hero Image" text, overlay title/subtitle if present | Must render `block.image_url` as actual `<img>`, show placeholder only when URL is empty |
| `product-showcase-block.tsx` | Blue box with "Product Photo" text + name/brand/description | Must render `product.image_url` as actual image |
| `celeb-feature-block.tsx` | Purple circle with "Photo" text + name/description | Must render `celeb.image_url` as actual avatar |
| `image-gallery-block.tsx` | Gray boxes with alt text. Supports grid/carousel/masonry via CSS | Must render `img.url` as actual images. Carousel needs scroll behavior |
| `body-text-block.tsx` | Plain paragraphs, text-base, text-gray-700 | Needs editorial typography: serif font, larger line-height, optional drop cap |
| `pull-quote-block.tsx` | Border-left, Georgia italic, gray text | Decent starting point. Refine with larger font, centered layout option |
| `headline-block.tsx` | Needs verification | Should support level 1-3 with distinct sizing |
| `divider-block.tsx` | Needs verification | Should render line/space/ornament styles |
| `hashtag-bar-block.tsx` | Needs verification | Should render as pill-shaped tags |
| `credits-block.tsx` | Needs verification | Should render as formatted attribution list |

**Architecture is sound:** The `BlockRenderer` pattern (discriminated union + component registry) is exactly the right approach. Only the visual implementation of individual blocks needs upgrading.

### E2E: Known Gap Analysis

| Gap | Location | Impact | Fix |
|-----|----------|--------|-----|
| No startup env validation | `config.py` -- all fields `str \| None` | Runtime crash on first Gemini call | Add `@model_validator(mode='after')` to `Settings` |
| No health check endpoint | `api/app.py` | No way to verify setup before triggering | Add `GET /health` checking Supabase + env vars |
| Default graph has no checkpointer | `graph.py` line 115: `graph = build_graph()` | Default import uses no persistence | Verify `deps.py` builds graph with checkpointer for API use |
| No admin trigger UI | `admin/src/app/contents/page.tsx` | Must use curl for first pipeline run | Add button + form component |
| No seed data mechanism | Supabase tables may be empty | Source/enrich nodes return empty results | SQL seed script in `supabase/seeds/` |
| `curation_input.seed_keyword` vs `.keyword` | `pipeline.py` sends `seed_keyword`, curation reads `.keyword` | Pipeline may fail at first node | Verify and align field names |

---

## Confidence Assessment

| Feature Area | Confidence | Reason |
|-------------|------------|--------|
| E2E environment gaps | HIGH | Direct codebase analysis of `config.py`, `graph.py`, `pipeline.py`, `curation.py` reveals specific issues |
| Observability approach | HIGH | Verified google-genai SDK is used (not LangChain) making custom logging the correct choice; verified `usage_metadata` exists on responses |
| Magazine renderer gaps | HIGH | Read all 10 block component source files; gap between placeholder and real rendering is unambiguous |
| Feature complexity estimates | MEDIUM | Based on codebase structure, but Gemini API behavior, Supabase connection pooling, and Next.js Image optimization may surface unexpected issues |
| Token usage field names | MEDIUM | `response.usage_metadata` with `prompt_token_count` etc. should be verified against current google-genai SDK version at implementation time |

---

## Sources

### Codebase Analysis (PRIMARY)
- `/Users/kiyeol/development/decoded/editorial-ai-worker/src/editorial_ai/config.py` -- Settings model, env var definitions
- `/Users/kiyeol/development/decoded/editorial-ai-worker/src/editorial_ai/graph.py` -- Pipeline topology, default graph compilation
- `/Users/kiyeol/development/decoded/editorial-ai-worker/src/editorial_ai/state.py` -- Pipeline state schema
- `/Users/kiyeol/development/decoded/editorial-ai-worker/src/editorial_ai/services/editorial_service.py` -- 3-step editorial generation, google-genai SDK usage
- `/Users/kiyeol/development/decoded/editorial-ai-worker/src/editorial_ai/nodes/curation.py` -- Curation node, `curation_input.keyword` field access
- `/Users/kiyeol/development/decoded/editorial-ai-worker/src/editorial_ai/nodes/editorial.py` -- Editorial node wrapper
- `/Users/kiyeol/development/decoded/editorial-ai-worker/src/editorial_ai/nodes/review.py` -- Review node with retry logic
- `/Users/kiyeol/development/decoded/editorial-ai-worker/src/editorial_ai/api/routes/pipeline.py` -- Trigger endpoint, `seed_keyword` field
- `/Users/kiyeol/development/decoded/editorial-ai-worker/src/editorial_ai/api/routes/admin.py` -- Admin CRUD endpoints
- `/Users/kiyeol/development/decoded/editorial-ai-worker/src/editorial_ai/models/layout.py` -- MagazineLayout schema, 10 block types
- `/Users/kiyeol/development/decoded/editorial-ai-worker/admin/src/components/block-renderer.tsx` -- Block dispatch pattern
- `/Users/kiyeol/development/decoded/editorial-ai-worker/admin/src/components/blocks/hero-block.tsx` -- Placeholder rendering
- `/Users/kiyeol/development/decoded/editorial-ai-worker/admin/src/components/blocks/product-showcase-block.tsx` -- Placeholder rendering
- `/Users/kiyeol/development/decoded/editorial-ai-worker/admin/src/components/blocks/celeb-feature-block.tsx` -- Placeholder rendering
- `/Users/kiyeol/development/decoded/editorial-ai-worker/admin/src/components/blocks/image-gallery-block.tsx` -- Placeholder rendering
- `/Users/kiyeol/development/decoded/editorial-ai-worker/admin/src/lib/types.ts` -- TypeScript type definitions
- `/Users/kiyeol/development/decoded/editorial-ai-worker/supabase/migrations/001_editorial_contents.sql` -- Current DB schema

### External Research
- [LangChain UsageMetadataCallbackHandler](https://python.langchain.com/api_reference/core/callbacks/langchain_core.callbacks.usage.UsageMetadataCallbackHandler.html) -- Token tracking for LangChain calls (NOT applicable to native google-genai calls)
- [Langfuse LangGraph integration](https://langfuse.com/guides/cookbook/integration_langgraph) -- Alternative observability (evaluated and rejected as mandatory dependency)
- [LangSmith cost tracking](https://docs.langchain.com/langsmith/cost-tracking) -- Per-trace cost breakdown (opt-in, already configured)
- [LangSmith SDK Issue #1918](https://github.com/langchain-ai/langsmith-sdk/issues/1918) -- Per-node token dashboard feature request (confirms this is not natively available)
- [Storyblok: React dynamic component from JSON](https://www.storyblok.com/tp/react-dynamic-component-from-json) -- Pattern validation for block-based rendering approach
- [Langfuse vs LangSmith comparison](https://langfuse.com/faq/all/langsmith-alternative) -- Self-hosted observability options analysis
