# Project Research Summary

**Project:** Editorial AI Worker
**Domain:** Pipeline Observability + Dynamic Magazine Renderer + E2E Execution Setup
**Milestone:** v1.1 (builds on shipped v1.0)
**Researched:** 2026-02-26
**Confidence:** HIGH

## Executive Summary

The v1.1 milestone extends a working Editorial AI Worker — a 7-node LangGraph pipeline that generates magazine-quality content using Gemini 2.5 Flash, stores it in Supabase, and presents it in a Next.js admin dashboard for approval. The three v1.1 goals (E2E execution validation, pipeline observability, and dynamic magazine rendering) are architectural enhancements to an already-functional system, not greenfield work. Research confirms the scope is well-bounded and all three features can be implemented without adding significant new infrastructure: zero new Python dependencies, one frontend library (`motion` v12), one new Supabase table, and one SQL migration.

The recommended approach prioritizes E2E validation first because a confirmed working pipeline is the prerequisite for testing both observability (needs real data flowing through nodes) and the renderer (needs real Layout JSON with populated image URLs). Observability must be implemented at the application layer — not through LangChain callbacks — because the codebase uses the native `google-genai` SDK directly for all LLM calls, bypassing LangChain's callback system entirely. The magazine renderer is largely already built; the block architecture is correct and the work is upgrading 4 image-bearing block components from gray placeholder boxes to real image rendering, plus editorial typography improvements.

The two highest-risk items are both in E2E setup: a confirmed `seed_keyword` vs `keyword` field name mismatch between the API trigger endpoint and `curation_node` (guaranteed first-run failure without a fix), and potential Supabase `AsyncPostgresSaver` prepared statement errors when using the wrong connection pool port. Both are straightforward to fix once identified. The observability implementation has one critical subtlety: token metrics must be collected from `response.usage_metadata` on native google-genai responses, not via LangChain callback handlers that never fire for these calls.

## Key Findings

### Recommended Stack

The v1.0 stack (LangGraph 1.0.9, Gemini 2.5 Flash via native `google-genai` SDK, Supabase, FastAPI, Next.js 15 + Tailwind CSS 4) is unchanged for v1.1. The only net-new dependency is `motion` v12 for the admin dashboard — a React 19-compatible animation library (renamed from `framer-motion`) for scroll-reveal and entrance animations.

**Core v1.1 stack additions:**
- `motion` v12 (admin frontend, one `pnpm add`): Magazine-feel entrance animations and scroll reveals — React 19 compatible, ~50KB gzipped
- `time.monotonic()` (Python stdlib): Correct tool for measuring node wall-clock duration — `time.time()` produces unreliable results
- `pipeline_node_runs` Supabase table (new SQL migration): Persistent per-node execution metrics, FK to `editorial_contents.thread_id`, decoupled from LangGraph state
- `next/font/google` (already in Next.js 15): Editorial typography (Playfair Display for headlines, Noto Sans KR for Korean body) — zero new dependency

**What was evaluated and rejected:**
- LangSmith/Langfuse as mandatory dependency — already configured as opt-in (`LANGSMITH_TRACING=true`); custom Supabase logging gives the admin UI full control over displayed data
- OpenTelemetry/Jaeger — infrastructure-level overkill for 7 nodes and low-concurrency manual runs
- Three.js/GSAP in admin dashboard — consumer-facing viewer explicitly belongs in `decoded-app`; admin preview needs standard React + Tailwind
- `next/image` for external URLs — requires `remotePatterns` for each allowed domain; standard `<img>` with fallback is correct for arbitrary image sources from the pipeline

See `.planning/research/STACK.md` for full rationale, implementation patterns, and the complete list of new files to create.

### Expected Features

**Must have (table stakes — v1.1 milestone goals):**
- `curation_input` field name fix (`seed_keyword` vs `keyword` alignment) — guaranteed pipeline failure without this fix
- Environment variable validation at startup (Pydantic `@model_validator` fail-fast, not cryptic runtime errors)
- Supabase connection + table health check (`GET /health`) — verify connectivity before first pipeline run
- `AsyncPostgresSaver` connection validation with SSL guidance (port 5432 session pooler, not 6543 transaction pooler)
- Pipeline trigger button + keyword input form in Admin UI — currently no UI exists; requires curl/Postman for pipeline trigger
- Seed data SQL script for celebs/products/posts — empty Supabase tables produce empty magazine content
- Per-node execution timing (wall-clock) and token usage collection (from `response.usage_metadata` on google-genai responses)
- `pipeline_node_runs` Supabase table + migration SQL
- `GET /api/pipeline/runs/{thread_id}` endpoint
- Admin detail page pipeline log panel (accordion/timeline component)
- Upgrade 4 image-bearing blocks (hero, product, celeb, gallery) from placeholder boxes to real `<img>` rendering with fallback
- Block-level React Error Boundaries in `BlockRenderer`
- Defensive empty-state rendering for all 10 block types

**Should have (low effort, high value differentiators):**
- Token cost estimation display in log panel (Gemini 2.5 Flash pricing × token counts = ~$0.03/run)
- Side-by-side JSON + rendered view on content detail page (layout change only, components already exist)
- Pipeline progress status indicator in content list view (current node name)
- Responsive preview mode toggle (mobile/tablet/desktop width switching)
- Magazine-quality typography system (Google Fonts via `next/font/google`)

**Defer to post-v1.1:**
- Real-time pipeline progress via SSE (`astream_events()`) — high complexity, acceptable 2-min wait for now
- Prompt playground (edit/test prompts in Admin) — significant scope, iterate in code first
- Pipeline A/B comparison view — needs multiple accumulated runs first
- Magazine theme variants — establish one solid theme before adding variants
- PDF/print export — screenshot suffices for stakeholder reviews
- Node-level re-run from Admin — complex checkpoint manipulation, full re-trigger is sufficient

**Explicit anti-features — do not build:**
- LangSmith/Langfuse as mandatory runtime dependency — opt-in via env vars is correct
- Full CMS visual editor (drag-drop blocks) — the pipeline generates layout, admin reviews it; visual editor contradicts core value
- Canvas/WebGL/Three.js in admin renderer — consumer-facing experience lives in `decoded-app`
- Block-level inline editing in preview — two-way sync between JSON and DOM is a maintenance nightmare
- Automated cost alerting/budgets — pipeline runs are manual, display per-run cost and monitor manually

See `.planning/research/FEATURES.md` for full feature table with complexity estimates and the complete dependency graph.

### Architecture Approach

The v1.1 architecture extends three existing layers without adding new tiers. The backend gains a `node_wrapper` decorator in `observability.py` that wraps all 7 nodes at `build_graph()` time (not in individual node files), and a `preflight.py` module that validates all service connections at FastAPI startup lifespan. The database gains one new table (`pipeline_node_runs`) with a FK to `editorial_contents.thread_id`. The frontend gains two new components (`pipeline-timeline.tsx`, `preview-mode-toggle.tsx`) and visual enhancements to 10 existing block components. The Python Pydantic to TypeScript type contract is already established 1:1 and requires no changes.

**Major v1.1 components:**
1. `src/editorial_ai/observability.py` — `node_wrapper` decorator + `save_node_run()` fire-and-forget persistence; applied to all 7 nodes in `build_graph()`; observability failures are silently caught and never break the pipeline
2. `src/editorial_ai/preflight.py` — validates Supabase REST, Postgres checkpointer, Google AI, and optional LangSmith at FastAPI startup; populates `/health` endpoint with per-service status
3. `supabase/migrations/002_pipeline_node_runs.sql` — stores `thread_id`, `node_name`, `started_at`, `duration_ms`, `status`, `error_message`, `revision_count` with FK to `editorial_contents`
4. `src/editorial_ai/api/routes/pipeline.py` (modified) — adds `GET /api/pipeline/runs/{thread_id}` and `GET /api/pipeline/runs/recent` endpoints
5. `admin/src/components/pipeline-timeline.tsx` — horizontal timeline of node executions with green/red/gray status indicators on content detail page
6. Enhanced block components — 10 existing components upgraded in-place: real `<img>` rendering for hero/product/celeb/gallery, CSS-only carousel/masonry for galleries, editorial typography, defensive empty-state handling

**Key architectural constraints to respect:**
- Lean state principle: observability data goes in a separate Supabase table, NEVER in `EditorialPipelineState` (would bloat Postgres checkpoints and break resume for in-flight pipelines)
- Fire-and-forget pattern in `node_wrapper`'s `finally` block: `try/except pass` ensures Supabase failures never kill the pipeline
- Standard `<img>` not `next/image` for external image URLs (arbitrary domains require `remotePatterns` configuration in `next.config.ts`)
- 1:1 Python Pydantic to TypeScript type parity must be maintained: no frontend-only props that diverge from `layout.py` models

**Data flow change (v1.0 → v1.1):**
```
Before: Pipeline Node -> State Update -> Supabase (editorial_contents only)
After:  Pipeline Node -> node_wrapper() -> State Update + pipeline_node_runs INSERT (fire-and-forget)
                                              |
        Admin Dashboard -> GET /api/contents/{id}       -> Real images + magazine CSS
                        -> GET /api/pipeline/runs/{tid} -> Execution timeline
                        -> GET /health                  -> Service status
        Startup -> preflight_check() -> /health reports per-service status
```

See `.planning/research/ARCHITECTURE.md` for complete component inventory, build-order dependency graph, and all 5 anti-patterns to avoid.

### Critical Pitfalls

1. **`curation_input` key mismatch (`seed_keyword` vs `keyword`)** — `pipeline.py` sends `seed_keyword` but `curation_node` reads `.keyword`. First E2E run silently fails with "no seed keyword provided." Verified by direct codebase line references. Fix: audit all field names between API schemas and node state readers before first run; run `grep -r "seed_keyword" src/ && grep -r '"keyword"' src/editorial_ai/nodes/curation.py`.

2. **Supabase `AsyncPostgresSaver` prepared statement errors** — Using port 6543 (transaction pooler) instead of port 5432 (session pooler) produces intermittent `InvalidSqlStatementName` errors. Fix: verify `DATABASE_URL` uses port 5432; test with real Supabase connection string (not local PostgreSQL) before first pipeline run.

3. **Adding observability fields to `EditorialPipelineState` breaks existing checkpoints** — New TypedDict fields cause deserialization failures when resuming pipelines paused at `admin_gate` after deployment. Fix: store all observability data in the separate `pipeline_node_runs` table only — never in LangGraph state.

4. **Native `google-genai` SDK bypasses LangChain callbacks entirely** — The codebase uses `client.aio.models.generate_content()` directly; LangChain `CallbackHandler` (`on_llm_start`, `on_llm_end`) never fires for these calls. Hours wasted wiring up callbacks that produce nothing. Fix: collect token metrics from `response.usage_metadata` in each service method; use LangSmith `@traceable` decorator if individual LLM call tracing is needed.

5. **Dynamic renderer crashes on AI-generated empty blocks** — `create_default_template()` produces `HeroBlock(image_url="")`, `BodyTextBlock(paragraphs=[])`, `ProductShowcaseBlock(products=[])`. Fix: every block component needs defensive empty-state rendering; add `isBlockRenderable(block)` filter before rendering.

**Additional pitfalls confirmed by codebase analysis:**
- Gemini `usage_metadata` token counts can be inaccurate with image inputs; cross-validate with `count_tokens()` during initial E2E runs
- Node timing metrics are misleading when tenacity retry backoff is included in wall-clock time; track `attempt_count` separately from `total_elapsed_ms`
- Unknown block types in the discriminated union crash the renderer; add a fallback component to the `BLOCK_MAP` registry
- CORS failures for images loaded from arbitrary external URLs; use standard `<img>` with `onError` fallback, test with production image URLs

See `.planning/research/PITFALLS.md` for all 13 pitfalls with code-level verification, source links, and phase-specific warning table.

## Implications for Roadmap

The dependency structure is unambiguous and mandates a specific phase ordering. E2E setup is the hard prerequisite: observability needs real pipeline runs to produce data, and the renderer validation needs real Layout JSON with populated image URLs. The renderer is the only pillar that can partially proceed in parallel (using v1.0 demo mode data for visual testing), but full validation requires a working pipeline.

### Phase 1: E2E Execution Foundation

**Rationale:** Without a confirmed working pipeline (real Gemini calls, real Supabase data, confirmed checkpointer connectivity), neither observability nor renderer can be properly tested. This phase eliminates all first-run blockers before building on top of them. It also serves as developer onboarding documentation via `.env.example`.

**Delivers:** A fully operational pipeline triggered from the Admin UI, with startup validation, health checks, seed data, and confirmed end-to-end execution. The `e2e_smoke.py` script provides a repeatable validation artifact.

**Addresses features:**
- `curation_input` field name fix (the critical first-run blocker)
- Pydantic `@model_validator` for fail-fast env var validation at startup
- `preflight.py` module with per-service connectivity checks
- `GET /health` endpoint reporting per-service status
- Pipeline trigger button + keyword input form in Admin contents page
- Seed data SQL script for celebs/products/posts
- `.env.example` with all required variables documented
- Basic `scripts/e2e_smoke.py` (trigger → poll → approve → verify published)

**Avoids:** Pitfall #1 (key mismatch), Pitfall #2 (wrong connection pool port)

**Research flag:** Standard patterns — no additional research needed. All gaps identified by direct codebase analysis with specific file and line references. Implementation is configuration, scripting, and one field name fix.

### Phase 2: Pipeline Observability (Backend)

**Rationale:** Build the data collection layer before the Admin UI that consumes it. The `node_wrapper` decorator and Supabase table can be validated via direct API calls (`GET /api/pipeline/runs/{thread_id}`) before the timeline component exists. Building backend-first also serves as a debugging foundation for any issues surfaced during Phase 1 E2E runs.

**Delivers:** Per-node execution timing, token usage, error status, and revision count for all 7 pipeline nodes, persisted in Supabase and accessible via REST API.

**Addresses features:**
- `observability.py` with `node_wrapper` decorator and fire-and-forget `save_node_run()`
- Node wrapping in `build_graph()` (non-invasive; tests continue using `node_overrides`)
- `supabase/migrations/002_pipeline_node_runs.sql`
- `GET /api/pipeline/runs/{thread_id}` and `GET /api/pipeline/runs/recent` endpoints
- Token cost estimation logic (static Gemini 2.5 Flash pricing constants)

**Avoids:** Pitfall #3 (state bloat — metrics in separate table), Pitfall #5 (exception chain corruption — do not wrap individual API calls, instrument at node level), Pitfall #7 (log storage growth — store metadata only; full prompts only for failed nodes), Pitfall #8 (retry timing confusion — track `attempt_count` separately), Pitfall #9 (LangChain callbacks don't fire — use `response.usage_metadata` directly), Pitfall #12 (use `time.monotonic()` not `time.time()`)

**Research flag:** Standard patterns for `node_wrapper` decorator and Supabase persistence. One validation spot-check at implementation time: verify exact `response.usage_metadata` field names against the installed `google-genai` SDK version before building the token collection layer. Cross-validate with `count_tokens()` on first real run to detect accuracy issues (Pitfall #4, medium confidence).

### Phase 3: Magazine Renderer Enhancement (Frontend, parallelizable with Phase 2)

**Rationale:** Pure frontend CSS/component work with no backend dependencies beyond the already-working Layout JSON API from v1.0. The block renderer architecture is already correct — this is visual enhancement to existing components, not new architecture. Can proceed in parallel with Phase 2 once Phase 1 E2E is confirmed, using demo mode data for initial visual testing.

**Delivers:** Magazine-quality block rendering with real images, editorial typography, carousel and masonry gallery layouts, robust empty-state handling, and block-level error isolation.

**Addresses features:**
- Real `<img>` rendering with fallback for hero, product showcase, celeb feature, image gallery blocks
- CSS-only carousel (`overflow-x-auto scroll-snap-x` + `snap-start`) and masonry (`columns-2 gap-4`) for `ImageGalleryBlock`
- Google Fonts via `next/font/google` (Playfair Display for headlines, Noto Sans KR for Korean body)
- Drop caps and editorial leading/tracking for `BodyTextBlock`
- Decorative pull quote styling (large font, accent border)
- Block-level React Error Boundaries in `BlockRenderer`
- `isBlockRenderable(block)` utility with pre-render filter
- Fallback component in `BLOCK_MAP` for unknown block types
- `motion` v12 scroll-reveal entrance animations (`pnpm add motion`)
- `loading="lazy"` on all gallery images

**Avoids:** Pitfall #6 (empty blocks crash — defensive rendering), Pitfall #10 (unknown block type fallback), Pitfall #11 (image load error fallbacks), Pitfall #13 (lazy loading for images below fold)

**Research flag:** Standard patterns — Tailwind CSS 4 component enhancement. No additional research needed. Implementation note: use `<img>` not `next/image` for external URLs from the pipeline.

### Phase 4: Dashboard Integration

**Rationale:** Combines the observability API (Phase 2) and enhanced block components (Phase 3) into the complete Admin content detail page experience. Depends on both previous phases being complete. This is the phase that delivers the visible v1.1 milestone outcome.

**Delivers:** The complete v1.1 Admin experience — content detail page with pipeline execution timeline, per-node timing/status, token cost display, responsive preview toggle, and side-by-side JSON + rendered view.

**Addresses features:**
- `pipeline-timeline.tsx` on content detail page (horizontal node execution timeline with status indicators)
- Token cost display in log panel
- `preview-mode-toggle.tsx` (mobile/tablet/desktop width constraints)
- Side-by-side JSON + rendered view layout (CSS change, components exist)
- Pipeline progress status in content list table
- Updated `e2e_smoke.py` with observability assertions (verify 7 node run entries)

**Research flag:** Standard patterns — React component composition with existing shadcn/ui primitives. No additional research needed.

### Phase Ordering Rationale

- **E2E first** because it is the hard prerequisite: observability needs real pipeline data, renderer validation needs real Layout JSON with image URLs populated by the pipeline
- **Observability backend before dashboard** because the timeline component needs data to display and the API endpoints can be validated independently via curl after Phase 1 runs
- **Renderer in parallel with observability** because it has zero backend dependencies for the visual enhancement work; demo mode data from v1.0 is sufficient for visual testing
- **Dashboard integration last** because it depends on both the observability API (Phase 2) and the enhanced renderer components (Phase 3) being complete
- This ordering matches the dependency graph independently derived by both ARCHITECTURE.md and FEATURES.md — HIGH confidence in phase structure

### Research Flags

Phases with standard patterns (skip `research-phase`):
- **Phase 1 (E2E Setup):** Configuration and scripting against a well-understood existing codebase. All gaps identified by direct codebase line analysis, not speculation.
- **Phase 3 (Magazine Renderer):** Tailwind CSS 4 component enhancements. Well-established patterns. Block architecture already proven correct by codebase analysis.
- **Phase 4 (Dashboard Integration):** React component composition with existing shadcn/ui. No novel patterns required.

Phases warranting implementation-time validation (spot-check, not full `research-phase`):
- **Phase 2 (Observability):** Validate exact `response.usage_metadata` field names (`prompt_token_count`, `candidates_token_count`, `total_token_count`) against the installed `google-genai` version before building token collection. Cross-validate with `client.models.count_tokens()` on the first real E2E run to surface any accuracy issues. This is a medium-confidence concern that does not warrant blocking implementation — just validate before building the dashboard display layer.

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | Zero new Python dependencies; `motion` v12 confirmed React 19 compatible; all other additions are existing installed packages or stdlib. Technology choices are extensions of the confirmed-working v1.0 stack. |
| Features | HIGH | Based on direct codebase analysis of all node, service, block component, and API files. Feature gaps are unambiguous (placeholder vs real image, missing startup validation, no UI trigger). Complexity estimates are MEDIUM confidence for Gemini API token accuracy and Supabase connection edge cases. |
| Architecture | HIGH | `node_wrapper` decorator, `preflight.py`, and block component enhancements are all additive changes to well-understood existing components. 1:1 Python-TypeScript type parity is already established and working. Data flow changes are minimal (one new Supabase table, no new API contract). |
| Pitfalls | HIGH | 4 of 13 pitfalls verified by direct codebase line references (key mismatch, retry exception chain, state bloat, google-genai bypasses callbacks). Supabase pooler issue has corroborating GitHub issues and a project code comment acknowledging it. Token accuracy issue is MEDIUM — reported fixed in recent SDK versions but varies by input type (image vs text). |

**Overall confidence:** HIGH

### Gaps to Address

- **Token usage field name verification:** Confirm `response.usage_metadata.prompt_token_count`, `candidates_token_count`, `total_token_count` are the exact field names in the currently-installed `google-genai` version. Run `print(dir(response.usage_metadata))` on first real E2E run before building the token collection layer. Handle gracefully if field names differ.
- **`curation_input` canonical field name direction:** Research confirmed the mismatch exists (`seed_keyword` in API vs `keyword` in node) but the correct fix direction should be confirmed against the `TriggerRequest` schema and `EditorialPipelineState` TypedDict during Phase 1 implementation. Either side is fixable; pick the one that requires fewer cascading changes.
- **Supabase `DATABASE_URL` port verification:** Confirm the `.env.local` connection string uses port 5432 (session pooler) not 6543 (transaction pooler). This is an operational check before the first E2E run, not a code change.
- **google-genai retry exception type preservation:** Verify that the tenacity `@retry_on_api_error` decorator in service files uses `retry_if_exception_type` that will still fire correctly if observability instrumentation wraps service calls. Affects how deep Phase 2 instrumentation can reach into service methods.

## Sources

### Primary (HIGH confidence — codebase analysis)
- `src/editorial_ai/config.py` — Settings model, env vars, LangSmith configuration
- `src/editorial_ai/graph.py` — Pipeline topology, node registration, `node_overrides` pattern
- `src/editorial_ai/state.py` — `EditorialPipelineState` TypedDict, lean state principle
- `src/editorial_ai/services/editorial_service.py` — native google-genai SDK usage pattern
- `src/editorial_ai/nodes/curation.py` — `curation_input.keyword` field access (line 24, Pitfall #1)
- `src/editorial_ai/api/routes/pipeline.py` — `seed_keyword` trigger field (line 32, Pitfall #1)
- `src/editorial_ai/models/layout.py` — `MagazineLayout` Pydantic, 10 block types, `create_default_template()`
- `admin/src/components/block-renderer.tsx` — `BLOCK_MAP` discriminated union dispatch
- `admin/src/components/blocks/` (all 10 files) — current placeholder rendering vs required real rendering
- `admin/src/lib/types.ts` — TypeScript types mirroring Python Pydantic models 1:1
- `supabase/migrations/001_editorial_contents.sql` — current DB schema
- `src/editorial_ai/checkpointer.py` — `AsyncPostgresSaver` setup, acknowledged pooler note

### Primary (HIGH confidence — official documentation)
- [LangSmith: Trace LangGraph Applications](https://docs.langchain.com/langsmith/trace-with-langgraph) — auto-tracing via env vars, what is and is not captured
- [LangChain: UsageMetadataCallbackHandler](https://python.langchain.com/api_reference/core/callbacks/langchain_core.callbacks.usage.UsageMetadataCallbackHandler.html) — callback system scope (LangChain wrappers only, not native SDKs)
- [Gemini token counting docs](https://ai.google.dev/gemini-api/docs/tokens) — `usage_metadata` field definitions
- [Motion (formerly Framer Motion) React upgrade guide](https://motion.dev/docs/react-upgrade-guide) — React 19 compatibility confirmation

### Secondary (MEDIUM-HIGH confidence — verified bug reports and community)
- [Supabase + asyncpg prepared statement issues (GitHub #39227)](https://github.com/supabase/supabase/issues/39227) — Pitfall #2 source
- [AsyncPostgresSaver InvalidSqlStatementName (LangGraph #2755)](https://github.com/langchain-ai/langgraph/issues/2755) — Pitfall #2 corroboration
- [LangGraph checkpoint-postgres breaking change (GitHub #5862)](https://github.com/langchain-ai/langgraph/issues/5862) — Pitfall #3 source
- [Token count broken (googleapis/python-genai #470)](https://github.com/googleapis/python-genai/issues/470) — Pitfall #4 source
- [Thinking tokens not counted correctly (simonw/llm-gemini #75)](https://github.com/simonw/llm-gemini/issues/75) — Pitfall #4 corroboration (MEDIUM)
- [LangSmith SDK Issue #1918](https://github.com/langchain-ai/langsmith-sdk/issues/1918) — confirms per-node token counts not natively available in external dashboard
- [Supabase pooling and asyncpg fix](https://medium.com/@patrickduch93/supabase-pooling-and-asyncpg-dont-mix-here-s-the-real-fix-44f700b05249) — Pitfall #2 prevention pattern

---
*Research completed: 2026-02-26*
*Supersedes: v1.0 SUMMARY.md (2026-02-20)*
*Ready for roadmap: yes*
