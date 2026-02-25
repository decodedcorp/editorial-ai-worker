# Domain Pitfalls: v1.1 Features

**Domain:** Adding observability, dynamic rendering, and E2E execution to existing editorial AI pipeline
**Researched:** 2026-02-26
**Overall Confidence:** MEDIUM-HIGH (cross-referenced with codebase analysis, official docs, and community reports)

**Scope:** This document covers pitfalls specific to the v1.1 milestone: first live E2E run, pipeline observability/metrics, and dynamic magazine rendering. For foundational pipeline pitfalls (feedback loops, state bloat, SDK choices), see the original PITFALLS.md from v1.0 research.

---

## Critical Pitfalls

Mistakes that cause blocked progress, data loss, or require significant rework.

### Pitfall 1: First E2E Run -- curation_input Key Mismatch Between API and Node

**What goes wrong:** The pipeline trigger endpoint (`/trigger`) sends `{"seed_keyword": ..., "category": ...}` as `curation_input`, but `curation_node` reads `curation_input.get("keyword")`. The key is `seed_keyword` in the API but the node expects `keyword`. First real run silently produces `pipeline_status: "failed"` with "no seed keyword provided."

**Why it happens:** The pipeline was built with stubs and unit tests that directly set `curation_input: {"keyword": "..."}`. The API route was added later and uses `seed_keyword` (matching the `TriggerRequest` schema). Nobody caught the mismatch because there was never an integration test through the actual HTTP endpoint to the real node.

**Consequences:** First demo fails immediately. Debug cycle wastes hours because the error message ("no seed keyword") does not indicate the field name mismatch -- it looks like the keyword was not provided at all.

**Warning signs:**
- `pipeline.py` line 32 sends `"seed_keyword"` but `curation.py` line 24 reads `"keyword"`
- No integration test that goes through the full API -> graph -> real node path
- Unit tests use `curation_input: {"keyword": "..."}` directly

**Prevention:**
- Before E2E run, audit every field name between API schemas and node state readers
- Write one integration test that sends a real HTTP request to `/trigger` and asserts `pipeline_status != "failed"`
- Standardize: pick either `keyword` or `seed_keyword` everywhere

**Detection:** Run `grep -r "seed_keyword" src/ && grep -r '"keyword"' src/editorial_ai/nodes/curation.py` to find the mismatch.

**Phase:** E2E execution (must fix before first run)

**Confidence:** HIGH (verified by reading codebase -- `pipeline.py` line 32 vs `curation.py` line 24)

---

### Pitfall 2: Supabase Session Pooler + AsyncPostgresSaver Prepared Statement Errors

**What goes wrong:** `AsyncPostgresSaver.from_conn_string()` sets `prepare_threshold=0` (documented in `checkpointer.py` comment), which should disable prepared statements. However, under concurrent requests or after connection recycling, Supabase's Supavisor pooler can still produce `InvalidSqlStatementName` errors like `"prepared statement asyncpg_stmt_9 does not exist"`.

**Why it happens:** Supabase replaced PgBouncer with Supavisor. The transaction pooler (port 6543) does not support prepared statements at all. The session pooler (port 5432) does support them but has connection limits. If `from_conn_string` internally uses asyncpg with `statement_cache_size > 0`, the session pooler may work initially but fail under load when connections are recycled.

**Consequences:** Pipeline crashes intermittently during E2E runs. The error is non-deterministic, making it extremely hard to reproduce in local testing (which uses direct connections, not pooled).

**Warning signs:**
- `InvalidSqlStatementName` errors in production logs
- Errors that appear only under concurrent pipeline runs
- Using port 6543 (transaction pooler) instead of 5432 (session pooler)

**Prevention:**
- Verify you are using port 5432 (session pooler), not 6543 (transaction pooler)
- Test with the actual Supabase connection string, not a local PostgreSQL
- If errors persist, explicitly pass `statement_cache_size=0` in connection parameters
- Add a connection health check before pipeline runs
- Consider running `checkpointer.setup()` as a one-time migration, not on every app start

**Phase:** E2E execution (validate connection before first run)

**Confidence:** MEDIUM-HIGH (known issue in Supabase + asyncpg ecosystem; the project comment already acknowledges it)

**Sources:**
- [Supabase + asyncpg prepared statement issues (GitHub #39227)](https://github.com/supabase/supabase/issues/39227)
- [AsyncPostgresSaver InvalidSqlStatementName (LangGraph #2755)](https://github.com/langchain-ai/langgraph/issues/2755)
- [Supabase pooling and asyncpg fix (Medium)](https://medium.com/@patrickduch93/supabase-pooling-and-asyncpg-dont-mix-here-s-the-real-fix-44f700b05249)

---

### Pitfall 3: Adding Observability Fields to State Breaks Existing Checkpoints

**What goes wrong:** To track per-node metrics (tokens, timing, prompts), you add new fields to `EditorialPipelineState` (e.g., `node_metrics: list[dict]`). Existing checkpoints in PostgreSQL were written with the old schema. Resuming an interrupted pipeline (e.g., one paused at `admin_gate`) after deploying the schema change causes deserialization errors or silently drops the new fields.

**Why it happens:** LangGraph's `JsonPlusSerializer` serializes the full state dict. When deserializing old checkpoints, new required fields are missing. TypedDict does not enforce defaults at runtime, so the behavior is undefined -- sometimes the field is `None`, sometimes it raises `KeyError`, depending on how the node accesses it.

**Consequences:** All in-flight pipelines (paused at admin_gate) become unresumable after deployment. Human approvals that were pending are lost.

**Warning signs:**
- Deploying state schema changes while pipelines are paused at `admin_gate`
- `KeyError` or `TypeError` when resuming a pipeline after deployment
- New metric fields returning `None` when you expected an empty list

**Prevention:**
- Add new state fields with `Annotated[list[dict], operator.add]` and ensure nodes always check `state.get("field") or []` (which the codebase already does for existing fields -- maintain this pattern)
- Do NOT add required fields without defaults to the state TypedDict
- Before deploying schema changes, either: (a) approve/reject all pending pipelines, or (b) write a migration script that adds default values to existing checkpoints
- Store observability data in a separate table (e.g., `pipeline_runs`, `node_executions`) rather than in LangGraph state -- this is the recommended approach

**Phase:** Observability (architectural decision: state vs. external table)

**Confidence:** HIGH (verified against LangGraph checkpoint serialization behavior and breaking change reports)

**Sources:**
- [LangGraph checkpoint-postgres breaking change (GitHub #5862)](https://github.com/langchain-ai/langgraph/issues/5862)
- [AsyncPostgresSaver JSON serializable error (LangChain Forum)](https://forum.langchain.com/t/asyncpostgressaver-and-json-serializable-error/692)

---

### Pitfall 4: Gemini Token Usage Metadata Inaccuracy

**What goes wrong:** You build a token tracking dashboard using `response.usage_metadata.prompt_token_count` and `candidates_token_count` from the `google-genai` SDK. The numbers are wildly inaccurate -- production shows 950K prompt tokens where calculations estimate 85K. Cost projections based on these numbers are 10x off.

**Why it happens:** The Gemini API has had documented bugs in `usage_metadata` token counts, particularly with image inputs and file uploads. The `EditorialService` sends image bytes (Nano Banana layout images) through `generate_content`, which can trigger inflated token counts. Additionally, `thinking_token_count` (from Gemini 2.5 Flash thinking mode) may or may not be included in `candidates_token_count` depending on whether you use the Gemini Developer API vs. Vertex AI.

**Consequences:** Cost tracking dashboard shows misleading numbers. Budget alerts fire incorrectly. Per-node cost attribution is meaningless.

**Warning signs:**
- Token counts that seem impossibly high for the input size
- Mismatch between `count_tokens()` pre-call estimate and `usage_metadata` post-call result
- Different token counts for the same prompt between Gemini API and Vertex AI backends

**Prevention:**
- Cross-validate: call `client.models.count_tokens()` for a sample of requests and compare with `usage_metadata`
- Log both `count_tokens()` estimates and `usage_metadata` actuals during the initial E2E runs
- For cost tracking, use `count_tokens()` as the source of truth for input tokens and `usage_metadata.candidates_token_count` for output tokens
- Separate `thoughts_token_count` from `candidates_token_count` explicitly -- do not assume they are additive
- Pin the google-genai SDK version and revalidate token counts after any upgrade

**Phase:** Observability (token tracking implementation)

**Confidence:** MEDIUM (bug was reported fixed but accuracy varies by model and input type)

**Sources:**
- [Token count broken (googleapis/python-genai #470)](https://github.com/googleapis/python-genai/issues/470)
- [Thinking tokens not properly counted (simonw/llm-gemini #75)](https://github.com/simonw/llm-gemini/issues/75)
- [Gemini token counting official docs](https://ai.google.dev/gemini-api/docs/tokens)

---

## Moderate Pitfalls

Mistakes that cause delays, incorrect data, or degraded user experience.

### Pitfall 5: Observability Wrapper Breaks google-genai Async Call Patterns

**What goes wrong:** To collect per-node metrics, you wrap each Gemini call with timing and token tracking. The wrapper uses `time.time()` around `await client.aio.models.generate_content()`. But the wrapper inadvertently changes exception handling: `retry_on_api_error` (tenacity decorator) expects specific exception types (`errors.ClientError`, `errors.ServerError`), and wrapping the call changes the exception chain, causing retries to stop working.

**Why it happens:** The codebase uses `google-genai` SDK directly (not LangChain's ChatGoogleGenerativeAI), so there is no built-in callback system. Adding observability means manually wrapping each service method. If the wrapper catches exceptions to log them and re-raises, the tenacity `retry_if_exception_type` check may fail because the re-raised exception is wrapped.

**Consequences:** Retries silently break. Transient API errors that previously resolved with retry now cause pipeline failures. The failure rate increases but nobody connects it to the observability change.

**Warning signs:**
- Increased pipeline failure rate after adding observability wrappers
- Retry count always showing 0 or 1 in logs (retries not happening)
- `tenacity.RetryError` exceptions appearing that were not seen before

**Prevention:**
- Do NOT wrap individual API calls. Instead, instrument at the node level: measure time and collect `usage_metadata` after each node completes
- If you must wrap API calls, use a decorator that preserves the original exception type:
  ```python
  async def timed_generate(client, **kwargs):
      start = time.monotonic()
      try:
          response = await client.aio.models.generate_content(**kwargs)
          elapsed = time.monotonic() - start
          return response, elapsed
      except Exception:
          elapsed = time.monotonic() - start
          raise  # preserve original exception for tenacity
  ```
- Test that retries still work after adding observability (send a request that triggers a 429, verify it retries)

**Phase:** Observability (implementation approach)

**Confidence:** HIGH (verified by reading `curation_service.py` retry_on_api_error pattern)

---

### Pitfall 6: Dynamic Magazine Renderer Crashes on AI-Generated Edge Cases

**What goes wrong:** The Next.js magazine renderer receives `MagazineLayout` JSON from the API and renders each block by type. But AI-generated content produces edge cases the renderer does not handle: empty `paragraphs: []` in BodyTextBlock, `image_url: ""` in HeroBlock (from the default template), `celebs: []` in CelebFeatureBlock, or `products: []` in ProductShowcaseBlock. The renderer crashes or shows blank sections.

**Why it happens:** Looking at the actual codebase: `create_default_template()` in `layout.py` creates blocks with `image_url=""`, `paragraphs=[]`, and `products=[]`. The `enrich_from_posts_node` only fills blocks if matching data exists in `enriched_contexts`. If Supabase has no matching posts (common for new/niche keywords), the template blocks remain empty. The Pydantic models allow these empty values (they are valid per schema), but the frontend renderer assumes non-empty data.

**Consequences:** Magazine preview page shows broken images (empty `src=""`), empty sections, or crashes entirely. Admin cannot evaluate content quality because the preview is unusable.

**Warning signs:**
- `HeroBlock(image_url="")` in the default template
- `BodyTextBlock(paragraphs=[])` -- renders nothing
- `ProductShowcaseBlock(products=[])` -- empty showcase section
- No Supabase posts matching the curated keywords

**Prevention:**
- Defensive rendering: every block component must handle empty/missing data gracefully
  ```tsx
  // BAD
  <img src={block.image_url} />

  // GOOD
  {block.image_url ? (
    <img src={block.image_url} />
  ) : (
    <div className="placeholder">No image available</div>
  )}
  ```
- Add a `blocks.filter()` step in the renderer that removes blocks with no meaningful content before rendering
- Create a `isBlockRenderable(block)` utility that checks minimum data requirements per block type
- Test the renderer with the exact output of `create_default_template("test", "Test Title")` -- this is the worst-case input

**Phase:** Dynamic rendering (component implementation)

**Confidence:** HIGH (verified by reading `layout.py` default template and `enrich_from_posts.py` enrichment logic)

---

### Pitfall 7: Log Storage Growth from Full Prompt/Response Logging

**What goes wrong:** To build the observability dashboard, you log full prompts and LLM responses for every Gemini call. Each `curation_node` call makes 3+ Gemini API calls (research, subtopic expansion, extraction). Each `editorial_node` makes 3 calls (content generation, image generation, layout parsing) plus potential repair calls. A single pipeline run produces 10+ LLM calls. At ~5-20KB per prompt/response pair, each run generates 100-400KB of log data. With weekly batch runs of 5-10 articles, plus retries, this grows to multi-GB per month.

**Why it happens:** The instinct when adding observability is to "log everything." Prompts are large (trend context includes DB data, enriched contexts, feedback history). Responses include full JSON layout objects. Nobody calculates the storage cost upfront.

**Consequences:** Supabase database storage fills up. Query performance degrades as the log table grows. Free/Pro tier Supabase storage limits (8GB) are hit within months.

**Warning signs:**
- Log table size growing faster than content table
- Supabase storage usage alerts
- Dashboard queries becoming slow

**Prevention:**
- Log metadata only by default: model name, token counts, elapsed time, success/failure, first 200 chars of prompt
- Store full prompts/responses only for failed calls (for debugging)
- Add a TTL/retention policy: auto-delete detailed logs older than 30 days, keep summary metrics forever
- Calculate expected storage: (avg_prompt_size + avg_response_size) x calls_per_run x runs_per_week x 4 weeks
- Consider LangSmith for full trace storage instead of your own database (it is already configured in `config.py`)

**Phase:** Observability (storage design)

**Confidence:** HIGH (calculated from codebase: curation makes 3+ calls, editorial makes 3+ calls, review makes 1 call = 7+ per run minimum)

---

### Pitfall 8: Timing Metrics Mislead Because of Retry and Backoff

**What goes wrong:** You measure node execution time and display it on the dashboard. But `curation_node` wraps its Gemini calls with `@retry_on_api_error` (tenacity: exponential backoff, 3 attempts). A node that takes "45 seconds" might have spent 2 seconds on the actual API call and 43 seconds on backoff waits after two retries. The dashboard shows "curation is slow" when the real issue is API rate limiting.

**Why it happens:** Node-level timing captures wall-clock time including retries, backoff delays, and error handling. Without separating "API time" from "wait time" from "retry count," the metrics are uninterpretable.

**Consequences:** Team optimizes the wrong thing. Dashboard shows misleading performance data. Stakeholders get alarmed by "45-second curation" when the API call itself is fast.

**Warning signs:**
- High variance in node execution times (2s vs 45s for the same node)
- Node times that are suspiciously close to retry backoff intervals (1s, 2s, 4s, 8s...)
- No way to distinguish first-attempt time from total time

**Prevention:**
- Track three separate metrics per node: `attempt_count`, `total_elapsed_ms`, `first_attempt_elapsed_ms`
- Track per-API-call timing inside the retry loop, not outside it
- Log retry events separately: `{"event": "retry", "node": "curation", "attempt": 2, "error": "429 rate limited", "backoff_ms": 2000}`
- Display retry count alongside timing on the dashboard

**Phase:** Observability (metrics design)

**Confidence:** HIGH (verified: `retry_on_api_error` in `curation_service.py` uses `wait_exponential(min=1, max=60)`)

---

### Pitfall 9: google-genai SDK Does NOT Use LangChain Callbacks

**What goes wrong:** You try to add observability using LangChain's callback system (`CallbackHandler`, `on_llm_start`, `on_llm_end`) because LangSmith is already configured. But the codebase uses `google.genai.Client` directly -- NOT `ChatGoogleGenerativeAI` from `langchain-google-genai`. LangChain callbacks are never triggered because the LLM calls bypass LangChain entirely.

**Why it happens:** The project made a deliberate choice to use the native `google-genai` SDK for direct access to Google Search Grounding, image generation (Nano Banana), and vision capabilities that are not available through the LangChain wrapper. This is the correct architectural choice, but it means LangChain's observability ecosystem does not apply.

**Consequences:** Hours spent trying to wire up LangChain callbacks that never fire. LangSmith traces show graph-level events but no LLM call details. The observability gap is exactly where you need the most visibility.

**Warning signs:**
- LangSmith traces showing node transitions but no LLM call spans
- `from langchain_google_genai import ChatGoogleGenerativeAI` not used anywhere in the services
- `google.genai.Client.aio.models.generate_content()` called directly

**Prevention:**
- Accept that observability must be built at the application level, not via LangChain callbacks
- Use the `response.usage_metadata` from `generate_content()` responses directly
- Build a lightweight metrics collector that wraps the `genai.Client` or instruments each service method
- If LangSmith integration is desired for LLM calls, use the LangSmith SDK directly (not through LangChain callbacks):
  ```python
  from langsmith import traceable

  @traceable(name="gemini_generate")
  async def tracked_generate(client, **kwargs):
      response = await client.aio.models.generate_content(**kwargs)
      return response
  ```
- Alternatively, integrate with OpenTelemetry spans for vendor-neutral observability

**Phase:** Observability (architecture decision -- must decide approach before implementation)

**Confidence:** HIGH (verified by reading entire codebase: all LLM calls go through `google.genai.Client`, zero use of LangChain LLM wrappers)

---

### Pitfall 10: Discriminated Union Rendering Fails on Unknown Block Types

**What goes wrong:** The `MagazineLayout.blocks` field uses a discriminated union (`Field(discriminator="type")`) with 10 known block types. If a future pipeline version introduces a new block type, or if the AI hallucinates a type name (e.g., `"video_embed"` instead of `"image_gallery"`), the Pydantic validation fails and the entire layout is rejected -- not just the unknown block.

**Why it happens:** Pydantic discriminated unions are strict: if the `type` field does not match any variant, validation fails for the entire list. There is no "skip unknown" option in the current schema. The AI occasionally produces creative block types not in the schema.

**Consequences:** One bad block type in a 12-block layout causes the entire magazine to fail validation. The review node catches this as a format error, triggering a re-edit cycle that may not fix the underlying issue (the AI might produce the same creative type again).

**Warning signs:**
- `ValidationError` mentioning discriminator field `type`
- Review feedback repeatedly citing "format" failure
- The editorial agent re-generating similar layouts with the same unknown type

**Prevention:**
- In the renderer (frontend), use a block type registry with a fallback:
  ```tsx
  const BLOCK_RENDERERS = { hero: HeroBlock, headline: HeadlineBlock, ... };
  const renderer = BLOCK_RENDERERS[block.type] || FallbackBlock;
  ```
- In the pipeline, pre-filter blocks before Pydantic validation: remove blocks with unknown types rather than rejecting the whole layout
- Add a warning log when unknown block types are encountered (helps track AI hallucination patterns)
- In the editorial prompt, explicitly list allowed block types (already done in `build_layout_parsing_prompt`)

**Phase:** Dynamic rendering (frontend) + Review node (backend)

**Confidence:** MEDIUM-HIGH (verified schema in `layout.py`; AI hallucination of type names is a known pattern with structured output)

---

## Minor Pitfalls

Mistakes that cause friction but are quickly fixable.

### Pitfall 11: CORS and Authentication Gaps in Admin API for Magazine Preview

**What goes wrong:** The admin dashboard fetches magazine layout JSON from the FastAPI backend to render a preview. CORS is configured for the dashboard origin, but the magazine preview component makes additional requests (e.g., loading images from Supabase storage, fetching product thumbnails from external URLs). These cross-origin requests fail silently, showing broken images in the preview.

**Prevention:**
- The magazine renderer should handle image load errors with fallback placeholders
- Proxy external images through the backend or use Supabase storage URLs (same origin)
- Test the preview with actual production image URLs, not just localhost

**Phase:** Dynamic rendering

---

### Pitfall 12: `time.time()` vs `time.monotonic()` for Duration Tracking

**What goes wrong:** Using `time.time()` for execution timing. System clock adjustments (NTP sync, DST changes) can produce negative durations or time jumps.

**Prevention:**
- Always use `time.monotonic()` for measuring elapsed time
- Use `time.time()` only for timestamps (when the metric was recorded)

**Phase:** Observability

---

### Pitfall 13: Magazine Preview Performance with Many Image Blocks

**What goes wrong:** A magazine layout with 6+ `ImageGalleryBlock` images, a `HeroBlock` image, and multiple `ProductShowcaseBlock` thumbnails triggers 10+ simultaneous image loads in the browser. The preview page becomes slow and janky, especially on slower connections.

**Prevention:**
- Lazy load images below the fold with `loading="lazy"` or Intersection Observer
- Use Next.js `Image` component with built-in lazy loading and blur placeholder
- Limit gallery images to 4-6 per block in the renderer (even if the data has more)
- Add image dimensions to the layout schema to prevent layout shift

**Phase:** Dynamic rendering

---

## Phase-Specific Warnings

| Phase/Feature | Likely Pitfall | Mitigation |
|---------------|---------------|------------|
| E2E First Run | curation_input key mismatch (#1) | Audit API->node field names before first run |
| E2E First Run | Supabase pooler errors (#2) | Test with real Supabase connection string, not local PG |
| E2E First Run | Empty Supabase data -> empty magazine | Seed test data in posts/solutions tables first |
| Observability | State schema changes break checkpoints (#3) | Store metrics in separate table, not LangGraph state |
| Observability | google-genai not using LangChain callbacks (#9) | Build app-level instrumentation or use LangSmith @traceable |
| Observability | Token count inaccuracy (#4) | Cross-validate with count_tokens(), log both values |
| Observability | Retry timing confusion (#8) | Track per-attempt vs total time separately |
| Observability | Log storage growth (#7) | Log metadata only, full prompts only on failure |
| Dynamic Rendering | Empty blocks from default template (#6) | Defensive rendering for all block types |
| Dynamic Rendering | Unknown block type crashes (#10) | Block type registry with fallback component |
| Dynamic Rendering | Image loading performance (#13) | Lazy loading, Next.js Image component |

---

## Quick Decision Guide

Before implementing each feature, answer these questions:

**Observability:**
1. Where to store metrics? --> Separate Supabase table (NOT LangGraph state)
2. How to instrument? --> Node-level wrappers + `response.usage_metadata` (NOT LangChain callbacks)
3. What to log? --> Metadata always, full prompts only on failure
4. How to handle retries in timing? --> Track attempt count + per-attempt time separately

**Dynamic Rendering:**
1. What does worst-case input look like? --> `create_default_template()` output with all empty fields
2. How to handle unknown block types? --> Fallback component, not crash
3. How to handle missing images? --> Placeholder, not broken `<img>`

**E2E Execution:**
1. Is the API -> node field mapping correct? --> Audit `seed_keyword` vs `keyword`
2. Is there test data in Supabase? --> Seed posts/solutions before first run
3. Is the connection string correct (port 5432, not 6543)? --> Verify

---

## Sources

- [Supabase + asyncpg prepared statement issues (GitHub #39227)](https://github.com/supabase/supabase/issues/39227) - HIGH confidence
- [AsyncPostgresSaver InvalidSqlStatementName (LangGraph #2755)](https://github.com/langchain-ai/langgraph/issues/2755) - HIGH confidence
- [LangGraph checkpoint-postgres breaking change (GitHub #5862)](https://github.com/langchain-ai/langgraph/issues/5862) - HIGH confidence
- [Token count broken (googleapis/python-genai #470)](https://github.com/googleapis/python-genai/issues/470) - HIGH confidence
- [Thinking tokens not counted correctly (simonw/llm-gemini #75)](https://github.com/simonw/llm-gemini/issues/75) - MEDIUM confidence
- [Gemini token counting official docs](https://ai.google.dev/gemini-api/docs/tokens) - HIGH confidence
- [LangGraph observability with Langfuse](https://langfuse.com/guides/cookbook/example_langgraph_agents) - MEDIUM confidence
- [LangGraph + FastAPI + Postgres fight (Medium)](https://medium.com/@termtrix/i-built-a-langgraph-fastapi-agent-and-spent-days-fighting-postgres-8913f84c296d) - LOW confidence
- [Supabase pooling and asyncpg fix (Medium)](https://medium.com/@patrickduch93/supabase-pooling-and-asyncpg-dont-mix-here-s-the-real-fix-44f700b05249) - MEDIUM confidence
- [LangGraph token usage tracking (LangChain Forum)](https://forum.langchain.com/t/how-to-obtain-token-usage-from-langgraph/1727) - MEDIUM confidence
- [OpenTelemetry instrumentation for LangChain/LangGraph (Last9)](https://last9.io/blog/langchain-and-langgraph-instrumentation-guide/) - MEDIUM confidence
- Codebase analysis: `pipeline.py`, `curation.py`, `editorial_service.py`, `layout.py`, `checkpointer.py`, `state.py` - HIGH confidence
