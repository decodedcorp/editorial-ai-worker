# Project Research Summary

**Project:** Editorial AI Worker (Fashion editorial content auto-generation)
**Domain:** Multi-agent editorial AI pipeline — fashion content generation
**Researched:** 2026-02-20
**Confidence:** MEDIUM-HIGH

## Executive Summary

This project builds a production multi-agent pipeline that auto-generates fashion editorial content for the decoded-app. The architecture follows a deterministic, sequential workflow — Curation -> Source -> Editorial -> Review -> Admin Gate -> Publish — implemented as a LangGraph StateGraph with Postgres-backed checkpointing. The recommended approach is a supervisor-style orchestration (not swarm) using LangGraph 1.0.8 GA with Gemini 2.5 Flash as the primary LLM, Supabase pgvector for vector search, and Perplexity Sonar for trend research. Google Cloud Run is the deployment target given the long-running nature of LLM pipelines (minutes, not seconds), making Cloudflare Workers unsuitable despite the repo name.

The most important architectural decisions must be made in Phase 1 before writing any agent logic: lean state schema design (store IDs and references, not full payloads), the `langchain-google-genai` SDK (not the deprecated `langchain-google-vertexai`), and bounded feedback loops with hard retry caps. These three decisions are expensive to change retroactively and affect every downstream phase. The Magazine Layout JSON schema — the contract between this worker and decoded-app's frontend — must be versioned from day one and validated at every node boundary.

The critical risks are all manageable with upfront design discipline: feedback loop death spirals (mitigated by max 3 retries + structured feedback schema), checkpoint state bloat (mitigated by lean state referencing Supabase IDs), Gemini structured output intermittent failures (mitigated by Pydantic validation + output repair), and HITL resume failures (mitigated by using `AsyncPostgresSaver` from integration testing onward, never `MemorySaver`). The feature scope for MVP is well-defined: 7 table-stakes features plus Source Agent and scheduling form a shippable v1.

## Key Findings

### Recommended Stack

The core stack is LangGraph 1.0.8 + `langchain-google-genai` 4.1.2 + Gemini 2.5 Flash + Supabase (Postgres + pgvector) + FastAPI on Cloud Run. Python 3.12 is the target runtime. LangSmith provides native LangGraph tracing from day one. uv replaces pip/poetry for package management. The critical SDK migration note: `ChatVertexAI` from `langchain-google-vertexai` is deprecated as of late 2025 and will be removed June 2026 — the correct path is `ChatGoogleGenerativeAI(model="gemini-2.5-flash", project="...", location="us-central1")` from `langchain-google-genai` 4.x, which routes through Vertex AI while using the new unified `google-genai` SDK.

**Core technologies:**
- `langgraph>=1.0.8`: StateGraph orchestration for the editorial pipeline — GA, supervisor pattern, human-in-the-loop via `interrupt()`
- `langchain-google-genai>=4.1.2`: LangChain Gemini integration — replaces deprecated `ChatVertexAI`; use `ChatGoogleGenerativeAI` with `project` param
- `gemini-2.5-flash`: Primary LLM for editorial generation — best cost/quality ratio for structured content
- `gemini-2.5-flash-lite`: Curation and routing — 1.5x faster, lower cost for lightweight classification tasks
- `gemini-embedding-001`: Embeddings for vector search — top MTEB multilingual scores, unified billing
- `langgraph-checkpoint-postgres>=2.0.0`: Durable state for HITL pause/resume — direct Supabase Postgres connection
- Supabase pgvector: Vector storage co-located with relational data — no separate vector DB needed at editorial content scale
- Perplexity Sonar: Trend research and source finding — purpose-built for citations, $1/M tokens
- `fastapi>=0.129.0` + `uvicorn>=0.34.0`: Admin dashboard API and pipeline triggers — async-native, Pydantic integration
- `pydantic>=2.12.5`: Single source of truth for Layout JSON schema, LLM output validation, API types
- LangSmith: Native LangGraph tracing — free tier, essential for multi-agent debugging
- `uv>=0.6.0`: Package management — 10-100x faster than pip, deterministic lockfiles

**What not to use:** `gemini-3-flash` (public preview, unstable), `ChatVertexAI` (deprecated), separate vector DB (Pinecone/Weaviate — pgvector sufficient), OpenAI embeddings (second vendor), Cloudflare Workers (CPU time limits incompatible with long-running pipelines).

### Expected Features

Full feature research in `.planning/research/FEATURES.md`.

**Must have (table stakes) — ship in MVP:**
- Trend keyword curation via Perplexity — pipeline entry point; without this content is stale
- Editorial Agent with 5 tool skills producing Magazine Layout JSON — core value, this IS the product
- LLM-as-a-Judge review with structured feedback — automated quality gate; binary pass/fail is insufficient
- Feedback loop with max retry (3 attempts) — evaluate-reflect-refine is industry standard pattern
- Celeb/influencer search from Supabase DB — editorial authority requires personality context
- Product/brand search from Supabase DB — commercial value requires shoppable product tie-in
- Human-in-the-loop admin approval (pending/approved/rejected) — mandatory for brand/legal risk management
- Admin content preview + approve/reject UI — approving a JSON blob is not acceptable
- Execution logging and traceability per pipeline run — non-negotiable for debugging multi-agent systems
- Retry limits and graceful failure — default 3, then escalate to human

**Should have (high-value differentiators to include in MVP):**
- Source Agent (Perplexity) — fact-grounded content with verifiable URLs separates from "AI slop"
- Structured feedback injection on retry — makes the feedback loop genuinely iterative, not naive retry
- Content scheduling (weekly cron) — operational necessity, low marginal complexity

**Defer to v2+:**
- Vector DB similarity search for dedup (use keyword dedup initially)
- SNS content integration (API access complexity)
- External reference collection via web scraping (fragile)
- Configurable editorial templates (start with one template)
- Quality analytics dashboard (collect metrics from day 1, visualize later)
- Multi-dimension review scoring breakdown (start with pass/fail + text feedback)

**Explicit anti-features — do not build:**
- Fully autonomous publishing without human gate
- AI-generated images (uncanny valley, copyright ambiguity)
- Real-time generation on user request (bypasses quality control)
- Complex WYSIWYG admin editor (frontend distraction)
- Multi-language support in v1 (doubles prompt engineering surface)
- Custom LLM fine-tuning (premature, no training corpus yet)

### Architecture Approach

The architecture is a LangGraph `StateGraph` with 6 nodes (Curation, Source, Editorial, Review, Admin Gate, Publish) connected by both direct edges and conditional edges that implement two feedback loops: an automatic Review->Editorial loop (bounded by `revision_count` <= 3) and a human-triggered Admin->Editorial loop. The `interrupt()` pattern freezes the pipeline at Admin Gate until `Command(resume=...)` is called from the admin dashboard API — zero compute while waiting. State flows as a typed `TypedDict` with `Annotated` reducers only for accumulating fields (error logs, tool call logs).

**Major components:**
1. **Curation Agent** (Node) — selects trending topics from Supabase celeb/products + Perplexity trend research; writes `curated_topics`
2. **Source Agent** (Node) — enriches curated topics with verified facts and URLs via Perplexity; deduplicates against vector DB; writes `enriched_contexts`
3. **Editorial Agent** (Node) — generates Magazine Layout JSON using Gemini 2.5 Flash with 5 bound tool skills; reads enriched context; writes `current_draft`
4. **Review Agent** (Node) — LLM-as-a-Judge scoring across tone, accuracy, brand voice, uniqueness; writes `review_result`; routes to revision or Admin Gate
5. **Admin Gate** (Node with `interrupt()`) — pauses pipeline for human approval; resumes via API call with decision + optional feedback
6. **Publish/Finalize** (Node) — writes approved content to Supabase, stores embedding in pgvector; idempotent
7. **Supabase service layer** (`supabase_service.py`) — thin wrapper for all DB operations; nodes never run raw queries
8. **Vector service layer** (`vector_service.py`) — `find_similar_posts()`, `store_post_embedding()`, `get_trending_keywords()`
9. **Perplexity service layer** (`perplexity_service.py`) — wrapped with retry logic and aggressive 30s timeout

**Key patterns:**
- Idempotent nodes — every node safe to re-execute on checkpointer resume
- Lean state — IDs and references only; full payloads live in Supabase, not LangGraph state
- Bounded feedback loops — `revision_count` hard cap prevents infinite cycling
- Structured output enforcement — Pydantic validation at every LLM output boundary
- Per-node error boundaries — try/except writes to `error_log` and sets `pipeline_status="failed"`
- Each node owns its own LLM instance with its own system prompt and temperature

**Editorial Agent implementation:** Start with Option A (single node with 5 bound tools via `llm.bind_tools([...])`). Promote to subgraph only when internal editorial routing becomes too complex for one node.

### Critical Pitfalls

Full pitfall research in `.planning/research/PITFALLS.md`.

1. **Feedback loop death spiral** — Review rejects indefinitely, burning tokens without quality improvement. Prevention: hard cap at 3 revisions (in state as `revision_count`), structured field-level feedback schema (not prose), monotonic quality check to break early. Must be built into graph topology in Phase 1 — retrofit is a node topology rewrite.

2. **Checkpoint state bloat** — Full editorial payloads (50KB+) duplicated across 15+ checkpoints per article. Prevention: lean state with only IDs/references; full content lives in Supabase; consider `durability="exit"` if intermediate recovery is not needed. Must be decided in Phase 1 state schema design.

3. **ChatVertexAI deprecation landmine** — Building on the deprecated `langchain-google-vertexai` package forces a painful migration before June 2026 with 50-90% latency regression from gRPC to REST. Prevention: use `ChatGoogleGenerativeAI` from `langchain-google-genai` 4.x from day one. Day-one decision, expensive to change.

4. **Gemini structured output intermittent failures** — Flash models produce malformed JSON with complex nested schemas, especially Magazine Layout JSON. Prevention: Pydantic validation at every node, `OutputFixingParser` wrapper for repair, keep schema as flat as possible, detect truncation via `max_output_tokens`. Phase 1 (schema design) + Phase 2 (editorial agent).

5. **HITL resume failures** — Admin approves content hours later; `MemorySaver` loses state on restart; schema migrations break existing checkpoints. Prevention: use `AsyncPostgresSaver` from integration testing onward, run `checkpointer.setup()` as separate migration script, store approved content snapshot in Supabase so publish reads from content store not LLM state.

6. **Context window pollution on re-edits** — Each feedback iteration accumulates all prior agents' outputs; re-edited drafts degrade in quality. Prevention: pass only current draft + structured feedback + original brief to editorial agent on re-edit; never pass full message history across nodes.

7. **Perplexity as single point of failure** — Rate limits (429) and outages block batch article generation. Prevention: exponential backoff with jitter, serialize batch processing (sequential not parallel), cache results in vector DB.

## Implications for Roadmap

Research strongly supports a 6-phase build order matching the dependency chain in the pipeline. This order is not arbitrary — it mirrors the data flow, ensures each phase can be validated against real inputs, and front-loads the architectural decisions that are expensive to change.

### Phase 1: Foundation (State, Graph Skeleton, Services)

**Rationale:** Every agent depends on the state schema and service layers. Critical architectural decisions (lean state, SDK choice, checkpointer, Layout JSON schema) must be locked in here before any agent logic is written. Retroactive changes to state schema break checkpoints and require rewriting multiple agents.

**Delivers:** Compilable graph with stub nodes, Postgres checkpointer working, Supabase and vector service layers testable in isolation, Layout JSON schema defined as versioned Pydantic model.

**Addresses:** State schema design (core architecture), service layer abstractions, `langchain-google-genai` SDK setup, LangSmith tracing wired up.

**Avoids:** Pitfall 2 (checkpoint bloat), Pitfall 3 (deprecated SDK), Pitfall 4 (schema complexity), Pitfall 8 (context pollution — architectural decision).

**Research flag:** Standard patterns (LangGraph StateGraph construction is well-documented). No deep research needed.

### Phase 2: Data Pipeline (Curation Agent + Source Agent)

**Rationale:** These nodes produce `curated_topics` and `enriched_contexts` — the inputs that Editorial needs. They also exercise the service layers from Phase 1 with real data. Building Editorial before Curation/Source means testing Editorial with mocked data that may not reflect real complexity.

**Delivers:** Given a trigger, the pipeline selects trending celeb/product combinations from Supabase and enriches them with Perplexity-sourced facts and dedup checks against vector DB.

**Addresses:** Trend keyword curation (table stakes), Source Agent with Perplexity (MVP differentiator), celeb/product search from DB.

**Avoids:** Pitfall 7 (Perplexity rate limits — implement retry and timeout here), Pitfall 10 (embedding model lock-in — store model version as metadata from day one).

**Uses:** Perplexity Sonar, Supabase (celeb/products tables), pgvector, `gemini-embedding-001`.

**Research flag:** Needs attention for Perplexity rate limit handling and vector DB schema. Patterns exist but integration specifics need verification.

### Phase 3: Content Generation (Editorial Agent)

**Rationale:** Depends on enriched context from Phase 2. This is the core value of the product — maximum attention warranted. The 5 tool skills and Magazine Layout JSON structured output are the most complex and novel part of the build.

**Delivers:** Given enriched context, produces valid Magazine Layout JSON matching the versioned Pydantic schema.

**Addresses:** Editorial Agent with 5 tool skills (core differentiator), structured output (table stakes), Magazine Layout JSON schema.

**Avoids:** Pitfall 4 (Gemini structured output failures — validate every output, implement `OutputFixingParser`). Pitfall 3 (ensure `ChatGoogleGenerativeAI` is used, not `ChatVertexAI`).

**Uses:** Gemini 2.5 Flash with `with_structured_output()`, `langchain-google-genai 4.x`, `pydantic>=2.12.5`.

**Research flag:** Gemini structured output reliability with complex Layout JSON needs empirical testing. Run schema stress tests early. This phase likely benefits from `/gsd:research-phase` for the Layout JSON schema design specifically.

### Phase 4: Quality Loop (Review Agent + Bounded Feedback)

**Rationale:** Needs real drafts from Phase 3 to review — cannot build the review rubric in the abstract. The feedback loop is the first non-trivial conditional graph topology and the most critical system behavior to get right.

**Delivers:** Review agent scores drafts, routes to revision or approval, feedback loop terminates correctly at max retries, structured feedback improves editorial output across iterations.

**Addresses:** LLM-as-a-Judge review (table stakes), feedback loop with structured retry (table stakes + differentiator), multi-dimension scoring foundation.

**Avoids:** Pitfall 1 (death spiral — hard cap via `revision_count`, structured feedback schema, monotonic quality check), Pitfall 5 (judge inconsistency — temperature=0 for judge, calibration dataset, two-pass check: deterministic format validation first then LLM quality evaluation).

**Research flag:** LLM-as-a-Judge calibration needs empirical calibration data from Phase 3 outputs. Plan to build a 10-20 article calibration set before going live with review agent. Standard patterns exist for the graph topology.

### Phase 5: Human Gate + Publish

**Rationale:** Requires the full pipeline upstream to produce content worth approving, and requires the Postgres checkpointer from Phase 1 for `interrupt()` to work correctly. The `interrupt()`/`Command(resume=...)` HITL pattern is well-documented but has specific production requirements (never `MemorySaver`, content snapshot strategy).

**Delivers:** Pipeline pauses at Admin Gate with draft + review scores surfaced for human decision; admin approve/reject/revision-request resumes pipeline; approved content written to Supabase and indexed in vector DB; admin preview UI functional.

**Addresses:** Human-in-the-loop approval (table stakes), content preview (table stakes), publish to Supabase, vector DB update for future dedup.

**Avoids:** Pitfall 6 (HITL resume failures — `AsyncPostgresSaver` only, `checkpointer.setup()` as migration, content snapshot in Supabase before approval).

**Research flag:** Standard patterns. LangGraph `interrupt()`/`Command` is well-documented. Admin dashboard integration is straightforward API design.

### Phase 6: Triggers + Operations

**Rationale:** Operational concerns belong last — the pipeline must work end-to-end before adding cron and monitoring. But tracing (LangSmith) should be wired from Phase 1 even if operational dashboards come in Phase 6.

**Delivers:** Weekly cron trigger via Cloud Scheduler, per-article error isolation (article 3 failure does not kill articles 4-10), dead letter queue for failed articles, LangSmith traces accessible, batch size configured, Cloud Run deployment.

**Addresses:** Content scheduling (weekly cron, MVP), retry limits and graceful failure (table stakes), execution logging (table stakes — LangSmith integration).

**Avoids:** Pitfall 9 (partial failure recovery — per-article `try/except` with independent Supabase status tracking), Pitfall 7 (batch rate limiting — sequential processing with deliberate delays between batch items).

**Research flag:** Cloud Run deployment and Cloud Scheduler are standard GCP patterns. LangSmith auto-instrumentation is straightforward. No deeper research needed.

### Phase Ordering Rationale

- State schema and service layers come first because both the data pipeline AND the agent logic depend on them. There is no valid shortcut order.
- Data pipeline (Curation + Source) precedes Editorial because Editorial needs real enriched context to produce meaningful output for testing the structured output schema.
- Review Agent follows Editorial because it needs real drafts; building the rubric without seeing actual output is guesswork.
- Admin Gate follows Review because you need reviewed drafts worth approving, and because the `interrupt()` checkpointer must be validated with real state.
- Operations come last because adding cron and monitoring to a broken pipeline just adds noise.
- This order also front-loads all 4 critical pitfalls that are architectural (Pitfalls 1, 2, 3, 8) in Phases 1-2, ensuring they are never retrofitted.

### Research Flags

Phases likely needing deeper research during planning:
- **Phase 3 (Editorial Agent):** Magazine Layout JSON schema complexity and Gemini structured output reliability are empirically uncertain. Recommend `research-phase` specifically for the Layout JSON schema contract with decoded-app frontend and Gemini Flash structured output stress testing.
- **Phase 2 (Curation + Source):** Perplexity API rate limit behavior under batch load needs benchmarking. Vector DB schema design for multi-version embedding support.

Phases with standard patterns (skip research-phase):
- **Phase 1 (Foundation):** LangGraph StateGraph construction, `AsyncPostgresSaver` setup, and Pydantic model design are well-documented with official sources.
- **Phase 4 (Review + Feedback):** Conditional graph routing and bounded feedback loop patterns are well-documented in LangGraph. Calibration is empirical, not research.
- **Phase 5 (Human Gate):** LangGraph `interrupt()`/`Command` is well-documented. Standard API design.
- **Phase 6 (Operations):** Cloud Run + Cloud Scheduler + LangSmith are standard GCP/LangChain patterns.

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | Core technologies (LangGraph 1.0.8, langchain-google-genai 4.1.2, Gemini 2.5 Flash GA) verified against official PyPI, Google, and LangChain sources. Deprecation timeline confirmed via official GitHub discussion. |
| Features | MEDIUM | Fashion editorial AI is a niche domain. Table stakes derived from general AI content pipeline patterns + Zalando case study. Feature ordering is opinionated inference from research, not verified against a direct comparator. |
| Architecture | MEDIUM-HIGH | LangGraph patterns (StateGraph, interrupt, conditional edges, checkpointing) verified against official documentation. Editorial-specific node composition and state schema design are opinionated but grounded in official patterns. |
| Pitfalls | MEDIUM-HIGH | Critical pitfalls (death spiral, state bloat, SDK deprecation) are well-documented across multiple sources including official issue trackers. Gemini structured output issues confirmed on official Google Cloud Java issue tracker. HITL resume failure pattern confirmed in LangChain official docs. |

**Overall confidence:** MEDIUM-HIGH

### Gaps to Address

- **Magazine Layout JSON schema:** The exact schema contract between editorial-ai-worker and decoded-app frontend is not defined in research. This must be established with the frontend team before Phase 1 completes. All agent prompts, Pydantic models, and review rubrics depend on this contract.
- **Gemini 2.5 Flash structured output reliability for this schema:** Research identifies this as a known issue but actual failure rate depends on the specific Layout JSON schema complexity. Empirical testing needed in Phase 3 with the real schema.
- **Perplexity API tier and rate limits for batch workload:** Research identifies rate limiting as a critical pitfall but actual capacity planning depends on weekly article volume and content category. Needs benchmarking once article targets are defined.
- **Supabase celeb/products data model:** Research assumes these tables exist with relevant fields (celeb_id, product_id, etc.) but their actual schema in the existing decoded-app database is unverified. Service layer design in Phase 1 depends on this.
- **Admin dashboard integration contract:** The admin review UI is described as a separate frontend app. The API contract between editorial-ai-worker and that dashboard needs to be defined before Phase 5 build begins.

## Sources

### Primary (HIGH confidence)
- [LangChain Blog: LangChain and LangGraph 1.0](https://blog.langchain.com/langchain-langgraph-1dot0/) — LangGraph 1.0.8 GA confirmation
- [langchain-google-genai 4.0.0 Deprecation Discussion](https://github.com/langchain-ai/langchain-google/discussions/1422) — ChatVertexAI deprecation, migration path
- [Vertex AI Model Versions](https://docs.cloud.google.com/vertex-ai/generative-ai/docs/learn/model-versions) — Gemini 2.5 Flash GA, Gemini 3 Flash preview
- [Gemini Structured Output Issues](https://github.com/googleapis/google-cloud-java/issues/11782) — Official issue tracker confirming Flash malformed JSON issue
- [LangGraph Interrupts - Official Documentation](https://docs.langchain.com/oss/python/langgraph/interrupts) — interrupt() and Command patterns
- [Perplexity API Rate Limits](https://docs.perplexity.ai/guides/usage-tiers) — Official rate limit tiers
- [LangChain Human-in-the-Loop Docs](https://docs.langchain.com/oss/python/langchain/human-in-the-loop) — HITL patterns
- [Why Do Multi-Agent LLM Systems Fail? (arXiv)](https://arxiv.org/html/2503.13657v1) — Peer-reviewed failure mode analysis
- [Vertex AI Structured Output Docs](https://docs.google.com/vertex-ai/generative-ai/docs/multimodal/control-generated-output) — OpenAPI schema limitations
- [Supabase pgvector Docs](https://supabase.com/docs/guides/database/extensions/pgvector) — HNSW indexing
- [LangGraph Graph API Overview](https://docs.langchain.com/oss/python/langgraph/graph-api) — StateGraph, edges, compilation

### Secondary (MEDIUM confidence)
- [LangGraph Best Practices - Swarnendu De](https://www.swarnendu.de/blog/langgraph-best-practices/) — Production patterns
- [Mastering LangGraph State Management 2025](https://sparkco.ai/blog/mastering-langgraph-state-management-in-2025) — TypedDict and reducer patterns
- [LangGraph Checkpointing Best Practices 2025](https://sparkco.ai/blog/mastering-langgraph-checkpointing-best-practices-for-2025) — MemorySaver vs Postgres
- [LLM-as-a-Judge Complete Guide - Evidently AI](https://www.evidentlyai.com/llm-guide/llm-as-a-judge) — Judge patterns and calibration
- [Evaluator Reflect-Refine Loop Patterns - AWS](https://docs.aws.amazon.com/prescriptive-guidance/latest/agentic-ai-patterns/evaluator-reflect-refine-loop-patterns.html) — Feedback loop architecture
- [Gemini Structured Outputs: Good, Bad, Ugly](https://dylancastillo.co/posts/gemini-structured-outputs.html) — Flash reliability analysis
- [AI Fashion Trends 2026 - Fashion Diffusion](https://www.fashiondiffusion.ai/blog/ai-fashion-trends-2026) — Fashion editorial AI use cases
- [AI and Fashion E-Commerce Content - BoF](https://www.businessoffashion.com/articles/technology/bof-voices-ai-and-the-future-of-fashion-ecommerce-content/) — Zalando case study (70% AI-generated editorial)

### Tertiary (LOW confidence)
- [AI Agents for Content Generation Guide](https://kodexolabs.com/ai-agents-content-generation-guide/) — General content pipeline patterns, needs validation
- [LLM Tool-Calling in Production: Infinite Loop Failure Mode](https://medium.com/@komalbaparmar007/llm-tool-calling-in-production-rate-limits-retries-and-the-infinite-loop-failure-mode-you-must-2a1e2a1e84c8) — Retry death spiral patterns

---
*Research completed: 2026-02-20*
*Ready for roadmap: yes*
