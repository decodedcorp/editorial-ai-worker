# Architecture Patterns

**Domain:** Multi-Agent Editorial AI Content Pipeline
**Researched:** 2026-02-20
**Overall confidence:** MEDIUM-HIGH (LangGraph patterns well-documented; editorial-specific composition is opinionated inference)

---

## Recommended Architecture

### High-Level System Diagram

```
                        ┌──────────────┐
                        │  Cron Trigger │  (weekly)
                        │  / Admin API  │
                        └──────┬───────┘
                               │
                               v
┌──────────────────────────────────────────────────────────────────┐
│                     LangGraph Orchestrator                       │
│                                                                  │
│  ┌──────────┐    ┌───────────┐    ┌─────────┐    ┌───────────┐ │
│  │ Curation │───>│ Editorial │───>│ Review  │───>│  Admin    │ │
│  │  Agent   │    │   Agent   │    │  Agent  │    │  Gate     │ │
│  └────┬─────┘    └─────┬─────┘    └────┬────┘    └─────┬─────┘ │
│       │                │               │               │        │
│       │          ┌─────┴─────┐    feedback loop    interrupt()  │
│       │          │ 5 Tool    │    (conditional      (HITL)      │
│       │          │ Skills    │     edge back to                  │
│       │          └───────────┘     Editorial)                   │
│       │                                                         │
│  ┌────┴─────┐                                                   │
│  │  Source  │                                                   │
│  │  Agent   │                                                   │
│  └──────────┘                                                   │
└──────────────────────────────────────────────────────────────────┘
        │              │                │                │
        v              v                v                v
  ┌──────────┐  ┌───────────┐   ┌───────────┐   ┌──────────────┐
  │ Supabase │  │ Vector DB │   │ Perplexity│   │  Vertex AI   │
  │ (celeb,  │  │(embeddings│   │    API    │   │  (Gemini)    │
  │ products,│  │ past posts│   │ (search)  │   │  LLM Engine  │
  │  posts)  │  │ trends)   │   └───────────┘   └──────────────┘
  └──────────┘  └───────────┘
```

### Component Boundaries

| Component | Responsibility | Communicates With | External Dependencies |
|-----------|---------------|-------------------|----------------------|
| **Curation Agent** (Node) | Selects trending topics, celeb/product combos for the week | Source Agent, Editorial Agent (via state) | Supabase (celeb, products), Vector DB (trend keywords) |
| **Source Agent** (Node) | Gathers external references, verifies facts, enriches context | Curation Agent (reads curated topics from state) | Perplexity API, Vector DB (past posts for dedup) |
| **Editorial Agent** (Node) | Generates structured content using 5 tool skills | Source Agent (reads enriched context from state) | Vertex AI (Gemini), tool invocations |
| **Review Agent** (Node) | Quality gates: tone, accuracy, brand compliance, dedup check | Editorial Agent (reads draft from state) | Vector DB (similarity check), Vertex AI (evaluation) |
| **Admin Gate** (Node) | Human-in-the-loop approval before publish | Review Agent (reads reviewed draft from state) | Admin Dashboard (external UI via API) |
| **Publish/Finalize** (Node) | Writes approved post to Supabase, updates Vector DB | Admin Gate (reads approval from state) | Supabase (posts), Vector DB (new embedding) |

---

## State Schema Design

The state schema is the backbone of LangGraph orchestration. Every node reads from and writes partial updates to this shared state. Use `TypedDict` with `Annotated` reducers for fields that accumulate across nodes.

**Confidence: HIGH** -- This pattern is directly from LangGraph official documentation.

### Core State

```python
from typing import TypedDict, Annotated, Optional, Literal
from langgraph.graph.message import add_messages
import operator

class EditorialPipelineState(TypedDict):
    """Top-level state for the editorial pipeline graph."""

    # --- Curation Phase ---
    curation_input: dict              # Trigger params (week, category filters)
    curated_topics: list[dict]        # [{celeb_id, product_id, angle, trend_keywords}]

    # --- Source Phase ---
    enriched_contexts: list[dict]     # [{topic, sources, facts, past_post_overlap_score}]

    # --- Editorial Phase ---
    current_draft: Optional[dict]     # Structured JSON (Magazine Layout schema)
    tool_calls_log: Annotated[list[dict], operator.add]  # Accumulates tool usage

    # --- Review Phase ---
    review_result: Optional[dict]     # {passed: bool, feedback: str, scores: dict}
    revision_count: int               # Tracks feedback loop iterations

    # --- Admin Gate ---
    admin_decision: Optional[Literal["approved", "rejected", "revision_requested"]]
    admin_feedback: Optional[str]

    # --- Pipeline Meta ---
    pipeline_status: Literal["curating", "sourcing", "drafting", "reviewing", "awaiting_approval", "published", "failed"]
    error_log: Annotated[list[str], operator.add]  # Accumulates errors across nodes
    messages: Annotated[list, add_messages]         # LLM conversation history
```

### Design Principles for State

1. **Minimal and typed.** Every field has a clear owner (the node that writes it) and consumers (downstream nodes that read it). No kitchen-sink state objects.

2. **Reducers only for accumulation.** Use `Annotated[list, operator.add]` only for fields that genuinely accumulate (error logs, tool call logs, messages). Regular fields use last-write-wins (default).

3. **No transient values.** Intermediate computation stays inside node functions. Only persist what downstream nodes or the checkpointer need.

4. **Status field for routing.** `pipeline_status` drives conditional edges. Every node updates it.

---

## Data Flow

### Primary Path (Happy Path)

```
Cron Trigger
    │
    v
[Curation Agent]
    │  Reads: Supabase (celeb, products), Vector DB (trends)
    │  Writes: curated_topics, pipeline_status="sourcing"
    v
[Source Agent]
    │  Reads: curated_topics, Perplexity API, Vector DB (dedup)
    │  Writes: enriched_contexts, pipeline_status="drafting"
    v
[Editorial Agent]
    │  Reads: enriched_contexts, curated_topics
    │  Calls: 5 tool skills via Vertex AI (Gemini)
    │  Writes: current_draft (Magazine Layout JSON), pipeline_status="reviewing"
    v
[Review Agent]
    │  Reads: current_draft, enriched_contexts
    │  Checks: tone, accuracy, brand voice, dedup via Vector DB
    │  Writes: review_result, pipeline_status
    │
    ├── If review_result.passed == False AND revision_count < MAX_REVISIONS:
    │       Writes: pipeline_status="drafting", revision_count += 1
    │       Conditional edge -> back to [Editorial Agent]
    │
    └── If review_result.passed == True:
            Writes: pipeline_status="awaiting_approval"
            v
        [Admin Gate]  <-- interrupt() here
            │  Human reviews in Admin Dashboard
            │  Resume with Command(resume={"decision": ..., "feedback": ...})
            │  Writes: admin_decision, admin_feedback
            │
            ├── "approved" -> [Publish/Finalize]
            ├── "revision_requested" -> [Editorial Agent] (with admin_feedback)
            └── "rejected" -> END
```

### Feedback Loops

There are two feedback loops in this architecture:

1. **Review -> Editorial loop:** Automatic. The Review Agent scores the draft and, if below threshold, sends it back to Editorial with structured feedback. Bounded by `revision_count` (recommend max 3 revisions).

2. **Admin -> Editorial loop:** Human-triggered. If the admin requests revision, the pipeline resumes at Editorial with `admin_feedback` injected into state. Also bounded.

### Data Transformation at Each Stage

| Stage | Input Shape | Output Shape |
|-------|------------|--------------|
| Curation | `{week, filters}` | `[{celeb_id, product_id, angle, trend_keywords}]` |
| Source | `curated_topics[]` | `[{topic, sources[], facts[], overlap_score}]` |
| Editorial | `enriched_contexts[]` | `{magazine_layout_json}` (structured output) |
| Review | `current_draft` | `{passed, feedback, scores{tone, accuracy, brand, uniqueness}}` |
| Admin Gate | `review_result + current_draft` | `{decision, feedback}` |
| Publish | `current_draft + admin_decision` | Supabase row + Vector DB embedding |

---

## Graph Construction Pattern

```python
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.postgres import PostgresSaver  # production

builder = StateGraph(EditorialPipelineState)

# --- Add Nodes ---
builder.add_node("curation", curation_agent)
builder.add_node("source", source_agent)
builder.add_node("editorial", editorial_agent)
builder.add_node("review", review_agent)
builder.add_node("admin_gate", admin_gate_node)
builder.add_node("publish", publish_node)

# --- Add Edges ---
builder.add_edge(START, "curation")
builder.add_edge("curation", "source")
builder.add_edge("source", "editorial")
builder.add_edge("editorial", "review")

# Conditional: Review outcome
builder.add_conditional_edges(
    "review",
    route_after_review,  # function that reads state
    {
        "revision": "editorial",    # feedback loop
        "approve": "admin_gate",    # proceed to human gate
        "fail": END,                # max revisions exceeded
    }
)

# Conditional: Admin decision
builder.add_conditional_edges(
    "admin_gate",
    route_after_admin,
    {
        "approved": "publish",
        "revision_requested": "editorial",
        "rejected": END,
    }
)

builder.add_edge("publish", END)

# --- Compile with Checkpointer ---
checkpointer = PostgresSaver(conn_pool)  # Postgres for production
graph = builder.compile(checkpointer=checkpointer)
```

### Admin Gate Node with interrupt()

```python
from langgraph.types import interrupt, Command

def admin_gate_node(state: EditorialPipelineState):
    """Pauses pipeline for human approval."""

    # Surface draft + review to admin dashboard
    admin_response = interrupt({
        "draft": state["current_draft"],
        "review_scores": state["review_result"]["scores"],
        "review_feedback": state["review_result"].get("feedback", ""),
        "prompt": "Please review and approve, reject, or request revision."
    })

    return {
        "admin_decision": admin_response["decision"],
        "admin_feedback": admin_response.get("feedback"),
        "pipeline_status": (
            "published" if admin_response["decision"] == "approved"
            else "drafting" if admin_response["decision"] == "revision_requested"
            else "failed"
        ),
    }
```

**Resume from Admin Dashboard API:**

```python
from langgraph.types import Command

# Admin dashboard calls this endpoint
def handle_admin_decision(thread_id: str, decision: str, feedback: str = ""):
    config = {"configurable": {"thread_id": thread_id}}
    graph.invoke(
        Command(resume={"decision": decision, "feedback": feedback}),
        config=config
    )
```

---

## Editorial Agent -- Subgraph Pattern for Tool Skills

The Editorial Agent is the most complex node. It has 5 tool skills (e.g., headline writing, body generation, product placement, image caption, SEO optimization). Two implementation options:

### Option A: Single Node with Tool Binding (Recommended for Start)

```python
from langchain_google_vertexai import ChatVertexAI

llm = ChatVertexAI(model="gemini-2.0-flash", temperature=0.7)
editorial_llm = llm.bind_tools([
    headline_tool,
    body_generator_tool,
    product_placement_tool,
    image_caption_tool,
    seo_optimizer_tool,
])

def editorial_agent(state: EditorialPipelineState):
    """Single node that uses Gemini with bound tools to produce Magazine Layout."""
    # LLM decides which tools to call and in what order
    result = editorial_llm.invoke(state["messages"])
    # ... process tool calls, build Magazine Layout JSON
    return {"current_draft": magazine_layout, "pipeline_status": "reviewing"}
```

### Option B: Subgraph (When Complexity Grows)

If the editorial phase needs its own internal routing (e.g., different flows for different content types), extract it into a subgraph with its own internal state:

```python
editorial_subgraph = StateGraph(EditorialInternalState)
editorial_subgraph.add_node("plan", plan_content_structure)
editorial_subgraph.add_node("generate_sections", generate_sections)
editorial_subgraph.add_node("assemble", assemble_magazine_layout)
# ... internal edges
compiled_editorial = editorial_subgraph.compile()

# Use as node in parent graph via wrapper function
def editorial_agent(state: EditorialPipelineState):
    internal_input = transform_to_editorial_input(state)
    result = compiled_editorial.invoke(internal_input)
    return transform_to_pipeline_output(result)
```

**Recommendation:** Start with Option A. Promote to Option B only when the editorial logic becomes too complex for a single node. Premature subgraph extraction adds overhead without benefit.

---

## Patterns to Follow

### Pattern 1: Idempotent Nodes

**What:** Every node should be safe to re-execute. If a node fails partway, the checkpointer resumes from the beginning of that node.

**When:** Always. This is a LangGraph requirement for interrupt() and checkpointer correctness.

**Example:** The Publish node should check if the post already exists in Supabase before inserting to avoid duplicates on retry.

### Pattern 2: Bounded Feedback Loops

**What:** Every feedback loop (Review->Editorial, Admin->Editorial) must have a maximum iteration count stored in state.

**When:** Any conditional edge that routes backward in the graph.

**Why:** Unbounded loops can cause infinite LLM calls and runaway costs.

```python
def route_after_review(state: EditorialPipelineState) -> str:
    if state["review_result"]["passed"]:
        return "approve"
    if state["revision_count"] >= 3:  # MAX_REVISIONS
        return "fail"
    return "revision"
```

### Pattern 3: Structured Output Enforcement

**What:** Use Gemini's structured output mode (or Pydantic model binding) to guarantee the Magazine Layout JSON schema is respected.

**When:** Editorial Agent output, Review Agent scoring output.

**Why:** Downstream frontend consumes Magazine Layout JSON. Schema violations break the frontend.

### Pattern 4: Error Boundaries per Node

**What:** Each node wraps its logic in try/except, writes errors to `error_log` in state, and sets `pipeline_status="failed"` on unrecoverable errors.

**When:** All nodes. Especially Source Agent (Perplexity API can fail) and Editorial Agent (LLM can produce invalid output).

```python
def source_agent(state: EditorialPipelineState):
    try:
        # ... Perplexity calls, Vector DB queries
        return {"enriched_contexts": contexts, "pipeline_status": "drafting"}
    except PerplexityAPIError as e:
        return {
            "error_log": [f"Source Agent failed: {str(e)}"],
            "pipeline_status": "failed"
        }
```

---

## Anti-Patterns to Avoid

### Anti-Pattern 1: God State

**What:** Putting every piece of intermediate data in the graph state.

**Why bad:** State is persisted by the checkpointer on every node transition. Large state = slow checkpointing, high storage costs, and hard-to-debug serialization issues.

**Instead:** Keep state minimal. Intermediate LLM reasoning stays inside node functions. Only persist what the next node needs.

### Anti-Pattern 2: Unbounded Message Accumulation

**What:** Using `add_messages` reducer and never trimming the messages list.

**Why bad:** Messages list grows with every LLM call across every node. Context window overflow, increased token costs.

**Instead:** Trim or summarize messages at node boundaries. Each agent should manage its own conversation window, not accumulate across the full pipeline.

### Anti-Pattern 3: Shared LLM Instance Across Agents

**What:** Using one ChatVertexAI instance with the same system prompt for all agents.

**Why bad:** Each agent has a different persona and task. Shared prompts cause role confusion and degrade output quality.

**Instead:** Each node initializes its own LLM with its own system prompt and tool bindings.

### Anti-Pattern 4: Polling for Admin Approval

**What:** Building a loop node that repeatedly checks Supabase for admin decisions.

**Why bad:** Wastes compute, adds complexity, can miss timing.

**Instead:** Use `interrupt()` with the checkpointer. The pipeline is frozen until `Command(resume=...)` is called from the admin dashboard API. Zero compute while waiting.

---

## External Integration Boundaries

### Vertex AI (Gemini)

- **Used by:** Curation Agent, Editorial Agent, Review Agent
- **Pattern:** Each agent creates its own `ChatVertexAI` instance with specific model, temperature, and system prompt
- **Structured output:** Use `.with_structured_output(PydanticModel)` for agents that need guaranteed JSON schemas

### Supabase

- **Used by:** Curation Agent (read celeb/products), Publish node (write posts)
- **Pattern:** Thin service layer (`supabase_service.py`) wrapping Supabase client. Nodes call service functions, never raw Supabase queries
- **Auth:** Service role key, not user JWT (this is a backend worker)

### Vector DB

- **Used by:** Curation Agent (trend keywords), Source Agent (dedup), Review Agent (similarity), Publish node (store new embedding)
- **Pattern:** Separate `vector_service.py` with functions like `find_similar_posts()`, `store_post_embedding()`, `get_trending_keywords()`
- **Embedding model:** Use Vertex AI text-embedding model for consistency

### Perplexity API

- **Used by:** Source Agent only
- **Pattern:** Wrapped in `perplexity_service.py` with retry logic and rate limiting
- **Timeout:** Set aggressive timeout (30s) -- if Perplexity is slow, degrade gracefully with cached/partial results

### Admin Dashboard

- **Used by:** Admin Gate node (via interrupt)
- **Pattern:** Dashboard is a separate frontend app that calls the worker's API. The API endpoint accepts admin decisions and calls `graph.invoke(Command(resume=...), config)` to resume the pipeline
- **No direct DB polling.** The interrupt/resume pattern handles coordination

---

## Suggested Build Order

Build order is driven by dependency chains. You cannot test downstream nodes without upstream nodes producing state.

### Phase 1: Foundation (Build First)

**What to build:**
1. State schema (`EditorialPipelineState`)
2. Graph skeleton (nodes as stubs, edges defined)
3. Checkpointer setup (Postgres-backed)
4. Supabase service layer (read celeb/products/posts)
5. Vector DB service layer (basic CRUD for embeddings)

**Why first:** Everything depends on state schema and service layers. Stub nodes let you validate the graph topology compiles and routes correctly before adding LLM logic.

**Validation:** Graph compiles, stub nodes pass state through, checkpointer persists/resumes.

### Phase 2: Data Nodes (Curation + Source)

**What to build:**
1. Curation Agent (reads Supabase, selects topics)
2. Source Agent (calls Perplexity, queries Vector DB for dedup)
3. Seed data in Supabase (celeb, products for testing)

**Why second:** These nodes produce the input data that Editorial needs. They also exercise the service layers built in Phase 1.

**Validation:** Given test input, Curation produces topic list; Source enriches with real Perplexity results.

### Phase 3: Content Generation (Editorial Agent)

**What to build:**
1. Editorial Agent with Vertex AI (Gemini) integration
2. 5 tool skill definitions
3. Magazine Layout JSON schema (Pydantic model)
4. Structured output enforcement

**Why third:** Depends on enriched_contexts from Phase 2. This is the core value -- focus attention here.

**Validation:** Given enriched context, produces valid Magazine Layout JSON matching schema.

### Phase 4: Quality Loop (Review Agent + Feedback)

**What to build:**
1. Review Agent (tone, accuracy, brand, uniqueness scoring)
2. Conditional edge routing (pass/revise/fail)
3. Feedback loop with revision counter
4. Vector DB similarity check for dedup

**Why fourth:** Needs drafts from Phase 3 to review. The feedback loop is the first non-trivial graph topology.

**Validation:** Reviews a draft, scores it, routes to revision or approval correctly. Loop terminates at max revisions.

### Phase 5: Human Gate + Publish

**What to build:**
1. Admin Gate node with `interrupt()`
2. Resume API endpoint
3. Publish node (write to Supabase, store embedding in Vector DB)
4. Admin Dashboard integration (or mock)

**Why fifth:** Needs the full pipeline upstream to produce content worth approving. interrupt() requires the checkpointer from Phase 1.

**Validation:** Pipeline pauses at admin gate, resumes on Command, publishes to Supabase.

### Phase 6: Trigger + Operations

**What to build:**
1. Weekly cron trigger (Cloud Scheduler or similar)
2. Error monitoring and alerting
3. LangSmith or custom tracing integration
4. Batch processing (multiple topics per run)

**Why last:** Operational concerns. The pipeline must work end-to-end first.

**Validation:** Cron triggers pipeline, processes multiple topics, errors are logged and alerted.

### Build Order Dependency Diagram

```
Phase 1: Foundation
    │
    ├── State Schema ──────────────> used by ALL phases
    ├── Graph Skeleton ────────────> used by ALL phases
    ├── Checkpointer ──────────────> used by Phase 5 (interrupt)
    ├── Supabase Service ──────────> used by Phase 2, 5
    └── Vector DB Service ─────────> used by Phase 2, 3, 4, 5
         │
         v
Phase 2: Data Nodes
    │
    ├── Curation Agent ────────────> produces curated_topics
    └── Source Agent ──────────────> produces enriched_contexts
         │
         v
Phase 3: Content Generation
    │
    └── Editorial Agent ───────────> produces current_draft
         │
         v
Phase 4: Quality Loop
    │
    ├── Review Agent ──────────────> produces review_result
    └── Feedback Loop ─────────────> routes back to Editorial
         │
         v
Phase 5: Human Gate + Publish
    │
    ├── Admin Gate (interrupt) ────> pauses for human
    └── Publish Node ──────────────> writes to Supabase + Vector DB
         │
         v
Phase 6: Trigger + Operations
    │
    └── Cron, Monitoring, Tracing
```

---

## Scalability Considerations

| Concern | Current (Weekly batch) | Growth (Daily) | High Scale (On-demand) |
|---------|----------------------|----------------|----------------------|
| LLM calls | ~20-50 per run | ~100-200 per run | Rate limiting on Vertex AI becomes critical |
| State size | Small (single post) | Medium (batch of 5-10) | Consider map-reduce pattern for parallelism |
| Checkpointer | SQLite OK for dev | Postgres required | Postgres with connection pooling |
| Vector DB | Small index | Index grows, query stays fast | Partition by content type or date |
| Admin approval | Async, hours OK | Same-day turnaround needed | Batch approval UI, partial auto-approve |

---

## Sources

- [LangGraph Interrupts - Official Documentation](https://docs.langchain.com/oss/python/langgraph/interrupts) -- HIGH confidence, interrupt() and Command patterns
- [LangGraph Best Practices - Swarnendu De](https://www.swarnendu.de/blog/langgraph-best-practices/) -- MEDIUM confidence, production patterns
- [LangGraph Multi-Agent Workflows - LangChain Blog](https://blog.langchain.com/langgraph-multi-agent-workflows/) -- HIGH confidence, official multi-agent patterns
- [LangGraph Subgraphs - Official Documentation](https://docs.langchain.com/oss/python/langgraph/use-subgraphs) -- HIGH confidence, subgraph integration
- [LangGraph Graph API Overview](https://docs.langchain.com/oss/python/langgraph/graph-api) -- HIGH confidence, StateGraph, edges, compilation
- [Practical Guide for Production Agentic AI Workflows (arXiv)](https://arxiv.org/html/2512.08769v1) -- MEDIUM confidence, general multi-agent architecture best practices
- [AI Agents for Content Generation Guide](https://kodexolabs.com/ai-agents-content-generation-guide/) -- LOW confidence, general content pipeline patterns
- [Mastering LangGraph State Management 2025](https://sparkco.ai/blog/mastering-langgraph-state-management-in-2025) -- MEDIUM confidence, TypedDict and reducer patterns
