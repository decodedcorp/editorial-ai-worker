# Domain Pitfalls

**Domain:** Multi-agent editorial AI pipeline (LangGraph + Vertex AI)
**Researched:** 2026-02-20
**Overall Confidence:** MEDIUM-HIGH (multiple sources cross-referenced; some LangGraph/Vertex specifics verified against official docs)

---

## Critical Pitfalls

Mistakes that cause rewrites or major architecture changes.

### Pitfall 1: Feedback Loop Infinite Cycling (Review-Reject-Re-edit Death Spiral)

**What goes wrong:** The review agent repeatedly rejects the editorial agent's output, which re-edits and gets rejected again, burning tokens and time indefinitely. This is especially common when the judge's rubric is misaligned with what the editorial agent can actually fix, or when the feedback is too vague to be actionable.

**Why it happens:** No hard cap on retry iterations. The LLM-as-a-Judge rubric penalizes issues the editorial agent cannot resolve (e.g., "needs better celebrity photos" when the agent only has text tools). Feedback is qualitative ("make it better") instead of structured and actionable.

**Consequences:** Runaway API costs (each loop = multiple LLM calls + tool invocations). Cron job never completes. Content quality does not improve after 2-3 iterations --- it degrades as context window fills with prior failed attempts.

**Warning signs:**
- Average loop count per article exceeding 3 during testing
- Review feedback repeating the same critique across iterations
- Token usage per article growing linearly with no quality improvement
- Cron jobs timing out

**Prevention:**
- Hard cap: max 3 review-reject cycles, then escalate to human review with the best attempt so far
- Structured feedback schema: the judge must return specific field-level issues (e.g., `{"issues": [{"field": "body_paragraph_2", "type": "hallucination", "detail": "..."}]}`) not prose
- Gate check: before re-editing, verify the feedback contains actionable items the editorial agent actually has tools to fix
- Monotonic quality check: if score does not improve between iterations, break the loop early

**Phase:** Must be designed into the graph architecture from Phase 1 (graph skeleton). Retrofit is painful because it changes node topology.

---

### Pitfall 2: Checkpoint State Bloat from Large Editorial Payloads

**What goes wrong:** LangGraph creates a new checkpoint at every graph step. When state contains the full editorial content (article text, layout JSON, search results, celebrity data, product data), each checkpoint duplicates all of it. A single article generation with 10+ steps across agents writes hundreds of megabytes to the checkpoint store.

**Why it happens:** Teams store everything in the LangGraph state dict for convenience. LangGraph checkpoints the entire state at every node transition. With 5 tool calls on the editorial agent alone, plus curation, source, review, and re-edit steps, a single article can hit 15+ checkpoints.

**Consequences:** Database bloat (PostgreSQL / Supabase). Slow state loading on human-in-the-loop resume (admin approval may take hours/days). Storage costs scale multiplicatively with article count.

**Warning signs:**
- Checkpoint table growing faster than expected during integration testing
- State loading time exceeding 1 second
- Supabase storage warnings

**Prevention:**
- Store only references (IDs, URLs) in LangGraph state; keep full payloads in Supabase tables or external storage
- Use the LangGraph Store for cross-thread data rather than embedding in state
- Keep state lean: `{"article_id": "uuid", "status": "review", "score": 7.2}` not `{"full_article_json": {...50KB...}}`
- Consider `durability="exit"` mode if intermediate step recovery is not needed (writes checkpoint only at run end)

**Phase:** Must be decided in Phase 1 (state schema design). Migrating from fat state to lean state after building multiple agents is a rewrite.

---

### Pitfall 3: ChatVertexAI Deprecation and SDK Migration Landmine

**What goes wrong:** Team builds the entire pipeline on `langchain-google-vertexai` / `ChatVertexAI`, then discovers it is deprecated. Migration to `ChatGoogleGenerativeAI` (with `vertexai=True`) introduces 50-90% latency increases due to the switch from gRPC to REST transport, breaking production SLAs.

**Why it happens:** Tutorials and examples still reference `ChatVertexAI`. The deprecation was announced in late 2025 with `langchain-google-genai` 4.0.0. Teams new to the ecosystem do not know which package to start with.

**Consequences:** Either build on a deprecated package and face forced migration later, or migrate early and deal with latency regressions. Vertex AI SDK releases after June 2026 will not support Gemini at all.

**Warning signs:**
- Import warnings about deprecation in test runs
- Using `langchain-google-vertexai` package
- Latency spikes after any SDK upgrade

**Prevention:**
- Start with `langchain-google-genai` with `vertexai=True` from day one --- do not use `ChatVertexAI`
- Pin SDK versions and test latency before any upgrade
- Abstract the LLM client behind an interface so swapping implementations requires changing one file
- Monitor the LangChain Google integrations changelog: https://github.com/langchain-ai/langchain-google/discussions/1422

**Phase:** Phase 1 (environment setup). This is a day-one decision that is expensive to change.

---

### Pitfall 4: Gemini Structured Output Reliability Issues

**What goes wrong:** Gemini models intermittently produce malformed JSON when `responseSchema` is enforced, including looping text fragments, stray newline escape sequences, and output that exhausts the max token limit without completing the schema. This is especially problematic for the Magazine Layout JSON that the frontend must parse.

**Why it happens:** Known issue with Gemini Flash models and structured output. Schema complexity (deeply nested layout JSON with arrays of components, each with variant types) increases failure probability. The model sometimes enters a repetition loop when constrained by a complex schema.

**Consequences:** Frontend receives unparseable JSON. Pipeline silently produces corrupted content. If not caught by the review agent, broken layouts reach the admin approval queue, wasting human reviewer time.

**Warning signs:**
- JSON parse errors in test runs, especially with complex nested schemas
- Output token usage hitting max without completing the response
- Repeated fragments in generated JSON

**Prevention:**
- Use Pydantic models for schema definition and validate every output before passing to the next node
- Implement an `OutputFixingParser` wrapper that uses a second LLM call to repair malformed output
- Keep the Layout JSON schema as flat as possible; move deeply nested structures to separate tool calls
- Set a reasonable `max_output_tokens` and detect when it is exhausted (indicates truncation, not completion)
- Have the review agent explicitly validate JSON parsability as the first check before content quality
- Test with both Gemini Pro and Flash; Pro is more reliable for complex structured output but slower/costlier

**Phase:** Phase 1 (output schema design) and Phase 2 (editorial agent implementation). The schema flattening decision affects both frontend contract and agent prompts.

---

## Moderate Pitfalls

Mistakes that cause significant delays or technical debt.

### Pitfall 5: LLM-as-a-Judge Inconsistency and Bias

**What goes wrong:** The review agent gives inconsistent scores for the same content across runs. It exhibits position bias (favoring content at the start), verbosity bias (longer = better), and self-enhancement bias (preferring its own generation style). One practitioner reported "one in every ten tests spits out absolute garbage."

**Why it happens:** LLM judges are inherently stochastic. Without calibration data and clear rubrics, the judge drifts. Single-LLM evaluation is brittle compared to human annotators, especially for subjective editorial quality.

**Warning signs:**
- Score variance > 1.5 points (on a 10-point scale) for the same content across runs
- All articles passing review (judge is too lenient) or none passing (too strict)
- Review scores not correlating with human quality assessments

**Prevention:**
- Use structured rubrics with explicit criteria and scoring anchors (e.g., "hallucination: 0 = none found, 5 = fabricated claims")
- Set temperature to 0 for the judge to minimize stochasticity
- Build a calibration set of 10-20 pre-scored articles; validate judge consistency against this set before going live
- Log all judge decisions with reasoning for human audit
- Consider a two-pass review: fast check (format, JSON validity, required fields) as deterministic code, then LLM judge only for content quality

**Phase:** Phase 3 (review agent). But the calibration dataset should be started in Phase 2 as editorial content is generated.

---

### Pitfall 6: Human-in-the-Loop Resume Failures

**What goes wrong:** Admin approves content hours or days after generation. The graph resume fails because: the checkpoint store is misconfigured, the state schema has changed between generation and approval, or the LLM context from the original run is lost.

**Why it happens:** Human-in-the-loop requires persistent checkpointing, but teams test with `MemorySaver` (in-memory, lost on restart) and forget to switch to `AsyncPostgresSaver` for production. Schema migrations during development break existing checkpoints.

**Consequences:** Admin clicks "approve" and nothing happens, or worse, the pipeline re-runs from scratch, generating different content than what was reviewed.

**Warning signs:**
- Using `MemorySaver` in any non-test environment
- No migration strategy for checkpoint schema changes
- Graph resume producing different output than the checkpointed state

**Prevention:**
- Use `AsyncPostgresSaver` (or Supabase PostgreSQL) from the start of integration testing
- Run `checkpointer.setup()` as a separate migration script, not in application runtime
- Store the approved content snapshot separately from the checkpoint (so approval publishes the exact content that was reviewed, not a re-generation)
- Design the post-approval flow as a simple publish step that reads from the content store, not from LLM state

**Phase:** Phase 4 (human-in-the-loop). But the checkpointer choice should be made in Phase 1.

---

### Pitfall 7: Perplexity API as Single Point of Failure

**What goes wrong:** The curation agent and source agent both depend on Perplexity API. Rate limits (429 errors), outages, or slow responses block the entire pipeline. Weekly cron triggers many articles at once, hitting burst limits.

**Why it happens:** Perplexity uses a leaky bucket rate limiter. Batch generation (weekly cron producing multiple articles simultaneously) can exhaust the burst capacity. No fallback search provider is configured.

**Consequences:** Weekly content generation partially or fully fails. Some articles get search results, others do not, creating inconsistent quality. Retry storms compound the rate limiting.

**Warning signs:**
- 429 errors in cron job logs
- Inconsistent search result quality between articles in the same batch
- Perplexity API response times exceeding 10 seconds

**Prevention:**
- Implement exponential backoff with jitter for Perplexity calls
- Serialize article generation (process articles sequentially, not in parallel) or add deliberate delays between batch items
- Cache Perplexity results in the vector DB so repeated queries for similar topics do not hit the API
- Budget for a higher usage tier if batch volume exceeds basic tier limits
- Design the curation agent to be idempotent: if interrupted, it can resume without duplicate work

**Phase:** Phase 2 (curation agent) for implementation, but capacity planning in Phase 1.

---

### Pitfall 8: Context Window Pollution in Multi-Agent Pipelines

**What goes wrong:** As content flows through curation -> editorial -> source -> review -> re-edit, each agent's context accumulates prior agents' full outputs. By the time the editorial agent gets feedback for re-editing (iteration 2+), its context contains: original curation data, first draft, all tool call results, source verification results, review feedback, and now must generate a revision. This exceeds practical context limits or degrades quality.

**Why it happens:** LangGraph state grows additively. Teams append to message lists without trimming. Gemini's large context window (1M+ tokens) creates a false sense of security --- models still degrade with cluttered context even when within limits.

**Consequences:** Quality degradation on re-edits. Increased latency and cost. Agent starts hallucinating or ignoring instructions buried deep in context.

**Warning signs:**
- Re-edited articles being worse than the first draft
- Token usage doubling on each feedback iteration
- Agent ignoring specific feedback points

**Prevention:**
- Each agent should receive a clean, curated context, not the full message history
- Use LangGraph's state channels to pass only relevant data between nodes (not full conversation)
- On re-edit: pass only the current draft, the structured feedback, and the original brief --- not the full history
- Implement a context summarization step before re-edit if needed

**Phase:** Phase 1 (state schema and graph design). This is an architectural decision about how nodes communicate.

---

## Minor Pitfalls

Mistakes that cause annoyance but are fixable without major refactoring.

### Pitfall 9: Cron Job Error Handling and Partial Failure Recovery

**What goes wrong:** Weekly cron triggers pipeline for 5-10 articles. Article 3 fails (API error, malformed data). The entire batch is marked as failed, or worse, the error is swallowed and partially-generated content sits in a broken state in Supabase.

**Prevention:**
- Process each article independently with its own try/except and status tracking
- Use per-article status in Supabase: `queued` -> `generating` -> `review` -> `pending_approval` -> `published` / `failed`
- Implement a dead letter queue: failed articles get logged with error context for manual retry
- Cron job should report success/failure counts, not just overall status

**Phase:** Phase 5 (cron and deployment).

---

### Pitfall 10: Vector DB Embedding Model Lock-in

**What goes wrong:** Team picks an embedding model (e.g., `text-embedding-004`), populates the vector DB with all historical posts, then discovers the model is deprecated or a better one exists. Re-embedding the entire corpus is expensive and time-consuming.

**Prevention:**
- Store the embedding model version as metadata alongside each vector
- Design the vector DB schema to support multiple embedding versions simultaneously
- Keep the raw text alongside embeddings so re-embedding is possible
- Start with a small corpus for validation before bulk-embedding everything

**Phase:** Phase 2 (vector DB setup).

---

### Pitfall 11: Magazine Layout JSON Schema Drift

**What goes wrong:** The Layout JSON schema evolves as the frontend (decoded-app) adds new component types or layout options. The editorial agent's prompt and Pydantic model fall out of sync with what the frontend expects, causing silent rendering failures.

**Prevention:**
- Define the Layout JSON schema as a shared Pydantic model in a package or contract file
- Version the schema and include the version in the output JSON
- Automated contract test: generate sample output -> validate against frontend's expected schema
- Change management process: schema changes require updating both the agent prompt and the frontend parser

**Phase:** Phase 2 (editorial agent) and ongoing.

---

## Phase-Specific Warnings

| Phase | Likely Pitfall | Mitigation |
|-------|---------------|------------|
| Phase 1: Graph Skeleton & State | Fat state design (#2), context pollution (#8), wrong SDK (#3) | Define lean state schema early; use `langchain-google-genai`; establish data-passing patterns between nodes |
| Phase 2: Curation & Editorial Agents | Perplexity rate limits (#7), Gemini structured output failures (#4), embedding lock-in (#10) | Implement retry logic, output validation, and schema versioning from the start |
| Phase 3: Review Agent & Feedback Loop | Infinite cycling (#1), judge inconsistency (#5) | Hard caps, structured feedback schema, calibration dataset |
| Phase 4: Human-in-the-Loop & Admin | Resume failures (#6), checkpoint bloat surfacing (#2) | Production checkpointer, content snapshot for approval |
| Phase 5: Cron & Production | Partial failure recovery (#9), batch rate limiting (#7) | Per-article error handling, sequential processing with delays |

---

## LangGraph-Specific Gotchas (Quick Reference)

| Gotcha | Detail |
|--------|--------|
| `MemorySaver` in prod | Only for testing. Use `AsyncPostgresSaver` or equivalent for any deployment. |
| `checkpointer.setup()` | Run as migration script, not in app runtime. Prevents permission errors and race conditions. |
| State schema changes | Break existing checkpoints. Version your state schema and handle migration. |
| Streaming + structured output | Structured output enforcement prevents token-by-token streaming. Plan UI accordingly. |
| Supervisor vs swarm | Supervisor pattern adds latency due to "translation" overhead. For linear pipelines, direct handoff between agents is better. |

## Vertex AI / Gemini-Specific Gotchas (Quick Reference)

| Gotcha | Detail |
|--------|--------|
| `ChatVertexAI` deprecated | Use `ChatGoogleGenerativeAI(model="gemini-2.5-flash", vertexai=True)` instead. |
| SDK after June 2026 | `langchain-google-vertexai` will stop supporting Gemini entirely. |
| gRPC -> REST latency | New unified SDK uses REST, 50-90% slower than old gRPC. Monitor and benchmark. |
| OpenAPI schema limits | `default`, `optional`, `maximum`, `oneOf` not supported in Vertex AI schemas. Keep schemas simple. |
| Structured output on Flash | Intermittent malformed JSON with complex schemas. Validate every output. |
| Gemini 3 tool calling bugs | `gemini-3-pro-preview` may call tools incorrectly. Prefer stable model versions. |

---

## Sources

- [LangGraph Multi-Agent Orchestration Guide (Latenode)](https://latenode.com/blog/ai-frameworks-technical-infrastructure/langgraph-multi-agent-orchestration/langgraph-multi-agent-orchestration-complete-framework-guide-architecture-analysis-2025) - MEDIUM confidence
- [Advanced Multi-Agent Development with LangGraph (Medium)](https://medium.com/@kacperwlodarczyk/advanced-multi-agent-development-with-langgraph-expert-guide-best-practices-2025-4067b9cec634) - LOW confidence
- [Why Do Multi-Agent LLM Systems Fail? (arXiv)](https://arxiv.org/html/2503.13657v1) - HIGH confidence (peer-reviewed)
- [LangGraph Checkpointing Best Practices 2025 (SparkCo)](https://sparkco.ai/blog/mastering-langgraph-checkpointing-best-practices-for-2025) - MEDIUM confidence
- [Gemini Structured Output Issues (GitHub)](https://github.com/googleapis/google-cloud-java/issues/11782) - HIGH confidence (official issue tracker)
- [langchain-google-genai 4.0.0 Deprecation Notice (GitHub)](https://github.com/langchain-ai/langchain-google/discussions/1422) - HIGH confidence (official discussion)
- [Vertex AI Structured Output Docs (Google Cloud)](https://docs.google.com/vertex-ai/generative-ai/docs/multimodal/control-generated-output) - HIGH confidence (official docs)
- [LLM Tool-Calling in Production: Infinite Loop Failure Mode (Medium)](https://medium.com/@komalbaparmar007/llm-tool-calling-in-production-rate-limits-retries-and-the-infinite-loop-failure-mode-you-must-2a1e2a1e84c8) - LOW confidence
- [Perplexity API Rate Limits (Official Docs)](https://docs.perplexity.ai/guides/usage-tiers) - HIGH confidence
- [LangChain Human-in-the-Loop Docs](https://docs.langchain.com/oss/python/langchain/human-in-the-loop) - HIGH confidence
- [Gemini Structured Outputs: Good, Bad, Ugly (Dylan Castillo)](https://dylancastillo.co/posts/gemini-structured-outputs.html) - MEDIUM confidence
- [State of Agent Engineering (LangChain)](https://www.langchain.com/state-of-agent-engineering) - MEDIUM confidence
