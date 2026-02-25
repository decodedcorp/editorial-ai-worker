# Phase 7: Admin Backend + HITL - Research

**Researched:** 2026-02-25
**Domain:** LangGraph interrupt/resume HITL + FastAPI admin API + Supabase content storage
**Confidence:** HIGH

## Summary

This phase replaces the `stub_admin_gate` and `stub_publish` nodes with real implementations, adds a FastAPI admin API layer, and stores review-passed content in Supabase. The three core technical challenges are: (1) LangGraph `interrupt()` / `Command(resume=)` pattern for pausing the pipeline at admin gate, (2) FastAPI endpoints that interact with both Supabase (content CRUD) and the LangGraph checkpointer (resume paused graphs), and (3) Supabase table design for editorial content with status tracking.

The existing codebase already has `admin_decision`, `admin_feedback`, and `pipeline_status` fields in `EditorialPipelineState`, and `route_after_admin` conditional edges in `graph.py`. The `stub_admin_gate` currently auto-approves. The `MagazineLayout` Pydantic model is well-defined. The `AsyncPostgresSaver` checkpointer and `get_supabase_client()` async singleton are both in place. This means the infrastructure is ready -- the work is wiring interrupt logic, building the API layer, and creating the Supabase content table.

**Primary recommendation:** Use LangGraph's `interrupt()` at the top of `admin_gate` node (before any side effects), store the content snapshot to Supabase as a side effect after interrupt returns, and expose FastAPI endpoints that call `graph.invoke(Command(resume=...), config)` to resume paused pipelines.

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| langgraph | 1.0.9 (installed) | Graph execution with interrupt/resume | Already in use; provides `interrupt()`, `Command` |
| fastapi | ~0.133.0 (latest) | Admin REST API | Async-native, Pydantic integration, auto OpenAPI docs |
| uvicorn | latest (via `fastapi[standard]`) | ASGI server | Standard FastAPI server |
| supabase | 2.28.0 (installed) | Content storage via REST API | Already in use for other services |
| langgraph-checkpoint-postgres | 3.0.4 (installed) | Persistent checkpointing for interrupt state | Already configured; survives server restarts |
| pydantic | 2.12.5+ (installed) | Request/response validation | Already in use throughout |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| httpx | (FastAPI dependency) | Test client for API testing | `pytest` + `httpx.AsyncClient` for endpoint tests |
| pydantic-settings | 2.8.0+ (installed) | Config management for new settings | Add `ADMIN_API_KEY`, `FASTAPI_HOST/PORT` |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| FastAPI | Litestar | FastAPI has wider ecosystem, more LangGraph examples; stick with FastAPI |
| Separate content table | LangGraph checkpoint only | Checkpoint stores full graph state but is opaque; dedicated table enables queries/filtering |

**Installation:**
```bash
uv add fastapi[standard]
# uvicorn comes bundled with fastapi[standard]
# No need for httpx separately -- it's a FastAPI test dependency
```

## Architecture Patterns

### Recommended Project Structure
```
src/editorial_ai/
  api/
    __init__.py
    app.py              # FastAPI app with lifespan (checkpointer init)
    routes/
      __init__.py
      admin.py           # approve/reject/list/detail endpoints
      pipeline.py        # trigger pipeline (optional)
    deps.py              # Dependency injection (graph, checkpointer)
    schemas.py           # Request/response Pydantic models
  nodes/
    admin_gate.py        # Real admin_gate node (interrupt pattern)
    publish.py           # Real publish node (status update)
  services/
    content_service.py   # Supabase content CRUD operations
```

### Pattern 1: LangGraph interrupt() in admin_gate Node
**What:** The `admin_gate` node calls `interrupt()` at the top to pause execution. When resumed via `Command(resume=...)`, the resume value contains the admin decision.
**When to use:** Every time the pipeline reaches admin review.
**Critical rule:** Place `interrupt()` at the TOP of the node. The node re-executes from the beginning on resume, so any code before `interrupt()` runs twice. Side effects (Supabase write) must come AFTER `interrupt()` or be idempotent.

```python
# Source: LangGraph official docs (https://docs.langchain.com/oss/python/langgraph/interrupts)
from langgraph.types import interrupt, Command

async def admin_gate(state: EditorialPipelineState) -> dict:
    """Pause for admin approval. Resume value determines next action."""
    # 1. Prepare snapshot for admin review (pure, no side effects)
    content_snapshot = {
        "current_draft": state.get("current_draft"),
        "review_result": state.get("review_result"),
    }

    # 2. interrupt() -- graph pauses here, snapshot surfaced to caller
    admin_response = interrupt(content_snapshot)

    # 3. After resume: admin_response contains decision
    #    e.g. {"decision": "approved"} or {"decision": "rejected", "reason": "..."}
    #    or {"decision": "revision_requested", "feedback": "..."}
    decision = admin_response["decision"]

    update: dict = {"admin_decision": decision}

    if decision == "rejected":
        update["admin_feedback"] = admin_response.get("reason", "")
        update["pipeline_status"] = "failed"
    elif decision == "revision_requested":
        update["admin_feedback"] = admin_response.get("feedback", "")
    elif decision == "approved":
        update["pipeline_status"] = "published"  # publish node will finalize

    return update
```

### Pattern 2: FastAPI Lifespan for Checkpointer Lifecycle
**What:** Use FastAPI's async lifespan context manager to initialize and teardown the Postgres checkpointer.
**When to use:** App startup/shutdown.

```python
# Source: FastAPI docs (https://fastapi.tiangolo.com/advanced/events/)
from contextlib import asynccontextmanager
from fastapi import FastAPI

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: initialize checkpointer
    async with create_checkpointer() as checkpointer:
        await checkpointer.setup()
        app.state.checkpointer = checkpointer
        app.state.graph = build_graph(checkpointer=checkpointer)
        yield
    # Shutdown: checkpointer cleaned up by context manager

app = FastAPI(lifespan=lifespan)
```

### Pattern 3: Resume via API Endpoint
**What:** Admin calls approve/reject endpoint, which invokes the graph with `Command(resume=...)` using the stored `thread_id`.
**When to use:** Every admin action.

```python
from langgraph.types import Command

@router.post("/contents/{content_id}/approve")
async def approve_content(content_id: str, request: Request):
    graph = request.app.state.graph
    thread_id = await get_thread_id_for_content(content_id)
    config = {"configurable": {"thread_id": thread_id}}

    result = await graph.ainvoke(
        Command(resume={"decision": "approved"}),
        config=config,
    )
    # Update content status in Supabase
    await update_content_status(content_id, "approved")
    return {"status": "approved", "content_id": content_id}
```

### Pattern 4: Content Storage in Supabase
**What:** Store review-passed content as a row in `editorial_contents` table with full Layout JSON in a `jsonb` column.
**When to use:** When content passes review (before interrupt).

**Recommendation on Claude's Discretion items:**

- **Storage unit:** Store full Layout JSON as `jsonb`. Normalizing blocks into separate tables adds complexity with no V1 benefit. The Layout JSON is the atomic unit the frontend renders.
- **Status model:** Use 4 states: `pending`, `approved`, `rejected`, `published`. Since rejection reason is mandatory, `rejected` needs to be a distinct terminal state separate from re-queued revisions. Revisions go back through the pipeline and create new pending entries.
- **Version history:** No history table in V1. The checkpointer already stores graph execution history. If needed later, add a `content_versions` table.
- **Curation context:** Do NOT duplicate in content table. The checkpointer has it. Store only `thread_id` as the link back to full pipeline context.
- **API framework:** FastAPI. Matches the roadmap, excellent async support, Pydantic model reuse.
- **Auth:** Simple API key via header (`X-API-Key`) checked in middleware. Trivial to add, prevents accidental access. No user auth system.
- **Admin notification:** Skip for V1. Dashboard polling (Phase 8) is sufficient.
- **Timeout:** No timeout for V1. Pending content waits indefinitely. Add configurable timeout later if needed.
- **Rejection handling:** Rejection is terminal for that content entry. Admin can manually re-trigger the full pipeline if needed. Auto-re-generation adds complexity without clear V1 value.
- **Publish action:** Status change only in V1. No external system integration.
- **Pipeline status:** Update `pipeline_status` in graph state at each transition. The content table status is separate from graph state status.
- **Content list/detail API:** Include in this phase. The admin needs to see pending content to approve/reject it.
- **Pipeline trigger API:** Include a basic trigger endpoint. Without it, testing the full flow requires CLI scripts, which blocks Phase 8 dashboard integration.

### Supabase Table Schema
```sql
CREATE TABLE editorial_contents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    thread_id TEXT NOT NULL,           -- LangGraph thread_id for resume
    status TEXT NOT NULL DEFAULT 'pending'
        CHECK (status IN ('pending', 'approved', 'rejected', 'published')),
    title TEXT NOT NULL,
    keyword TEXT NOT NULL,
    layout_json JSONB NOT NULL,        -- Full MagazineLayout JSON
    review_summary TEXT,               -- From ReviewResult.summary
    rejection_reason TEXT,             -- Required when status = 'rejected'
    admin_feedback TEXT,               -- Optional feedback on approve/revision
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    published_at TIMESTAMPTZ,          -- Set when status -> 'published'

    CONSTRAINT rejection_reason_required
        CHECK (status != 'rejected' OR rejection_reason IS NOT NULL)
);

CREATE INDEX idx_editorial_contents_status ON editorial_contents(status);
CREATE INDEX idx_editorial_contents_thread_id ON editorial_contents(thread_id);
```

### Anti-Patterns to Avoid
- **Side effects before interrupt():** The node re-executes from the top on resume. Any DB write before `interrupt()` will execute twice. Either make it idempotent (upsert) or place it after the interrupt.
- **Storing full state in content table:** The checkpointer already stores graph state. Don't duplicate `curated_topics`, `enriched_contexts`, etc. Store only what the admin needs to see.
- **Wrapping interrupt() in try/except:** LangGraph uses exceptions internally for interrupt flow control. Catching them breaks the mechanism.
- **Using graph.invoke() instead of graph.ainvoke():** This is an async codebase. Always use `ainvoke` in FastAPI async endpoints.
- **Creating a new graph per request:** Compile the graph once at startup with the checkpointer. Share it across requests via `app.state`.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Pipeline pause/resume | Custom queue + polling | LangGraph `interrupt()` + `Command(resume=)` | Handles state persistence, re-execution, edge cases |
| API request validation | Manual dict checking | Pydantic models + FastAPI auto-validation | Type safety, auto-docs, error messages |
| API documentation | Swagger file | FastAPI auto-generated OpenAPI | `/docs` endpoint free with FastAPI |
| State persistence across restarts | Custom DB state table | `AsyncPostgresSaver` checkpointer | Already configured, handles serialization |
| Content status transitions | If/else chains | Explicit status enum with DB CHECK constraint | Prevents invalid states at DB level |

**Key insight:** LangGraph's interrupt mechanism handles the hardest part (pausing a multi-step async pipeline and resuming exactly where it left off with full state). Don't try to replicate this with custom job queues or polling.

## Common Pitfalls

### Pitfall 1: Node Re-execution on Resume
**What goes wrong:** Code before `interrupt()` runs again when the node resumes, causing duplicate Supabase inserts or duplicate API calls.
**Why it happens:** LangGraph re-executes the entire node function from the beginning on resume. The `interrupt()` return value changes (returns the resume payload), but everything before it re-runs.
**How to avoid:** Place `interrupt()` at the very top of the node (or immediately after pure/read-only operations). All side effects (writes) must come after `interrupt()` returns.
**Warning signs:** Duplicate rows in Supabase, double-counted metrics.

### Pitfall 2: Missing thread_id Mapping
**What goes wrong:** Admin approves content but the API can't find which graph thread to resume because there's no mapping between `content_id` and `thread_id`.
**Why it happens:** Content is saved to Supabase but `thread_id` is not stored alongside it.
**How to avoid:** Always store `thread_id` in the `editorial_contents` table when saving content. This is the key that links admin actions back to the paused graph.
**Warning signs:** "Thread not found" errors on approve/reject.

### Pitfall 3: Checkpointer Not Initialized at Graph Compile Time
**What goes wrong:** Graph compiles without checkpointer, `interrupt()` silently fails or raises an error.
**Why it happens:** The default `graph = build_graph()` at module level has no checkpointer. FastAPI must compile a new graph with the checkpointer in the lifespan.
**How to avoid:** Use FastAPI lifespan to create checkpointer, then `build_graph(checkpointer=checkpointer)`. Never use the module-level `graph` object for interrupt-enabled flows.
**Warning signs:** `interrupt()` raises error about missing checkpointer, or graph runs through admin_gate without pausing.

### Pitfall 4: Async Context Manager Lifecycle
**What goes wrong:** Checkpointer connection pool exhausted or closed prematurely.
**Why it happens:** `create_checkpointer()` returns an async context manager. If not properly managed in FastAPI lifespan, connections leak or close before requests finish.
**How to avoid:** Use the lifespan pattern shown above. The `async with` ensures proper cleanup. Do NOT create a new checkpointer per request.
**Warning signs:** `ConnectionPool exhausted` errors, `connection closed` errors under load.

### Pitfall 5: Content Saved Before Interrupt with Stale Status
**What goes wrong:** Content saved as "pending" before interrupt, but if the server crashes before the graph state is checkpointed, the content exists in Supabase but no paused graph exists to resume.
**Why it happens:** Saving to Supabase and checkpointing are not in the same transaction.
**How to avoid:** Accept eventual consistency. The content save and checkpoint are close together temporally. Add a reconciliation query: "find pending contents with no matching paused thread" for cleanup.
**Warning signs:** Orphaned "pending" entries with no resumable thread.

## Code Examples

### admin_gate Node (Full Implementation Pattern)
```python
# Source: Verified against LangGraph docs + existing codebase patterns
from __future__ import annotations

import logging
from langgraph.types import interrupt
from editorial_ai.state import EditorialPipelineState

logger = logging.getLogger(__name__)

async def admin_gate(state: EditorialPipelineState) -> dict:
    """Pause pipeline for admin approval via LangGraph interrupt.

    The interrupt surfaces a content snapshot to the caller.
    On resume, the admin decision (approve/reject/revision) is returned
    as the interrupt() return value.
    """
    # Pure read -- safe to re-execute on resume
    snapshot = {
        "title": (state.get("current_draft") or {}).get("title", ""),
        "keyword": (state.get("current_draft") or {}).get("keyword", ""),
        "review_summary": (state.get("review_result") or {}).get("summary", ""),
    }

    # INTERRUPT -- graph pauses here
    # On initial run: raises interrupt, snapshot sent to caller
    # On resume: returns the Command(resume=...) value
    admin_response = interrupt(snapshot)

    # --- Everything below runs ONLY after resume ---
    decision = admin_response.get("decision", "rejected")

    update: dict = {"admin_decision": decision}

    if decision == "approved":
        logger.info("Admin approved content")
    elif decision == "revision_requested":
        update["admin_feedback"] = admin_response.get("feedback", "")
        logger.info("Admin requested revision: %s", update["admin_feedback"])
    else:  # rejected
        update["admin_feedback"] = admin_response.get("reason", "")
        update["pipeline_status"] = "failed"
        logger.info("Admin rejected content: %s", update["admin_feedback"])

    return update
```

### FastAPI App Skeleton
```python
# Source: FastAPI docs + project patterns
from __future__ import annotations

from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends, HTTPException, Security
from fastapi.security import APIKeyHeader

from editorial_ai.checkpointer import create_checkpointer
from editorial_ai.graph import build_graph

API_KEY_HEADER = APIKeyHeader(name="X-API-Key", auto_error=False)

@asynccontextmanager
async def lifespan(app: FastAPI):
    async with create_checkpointer() as checkpointer:
        await checkpointer.setup()
        app.state.checkpointer = checkpointer
        app.state.graph = build_graph(checkpointer=checkpointer)
        yield

app = FastAPI(title="Editorial AI Admin", lifespan=lifespan)
```

### Resume Graph from API
```python
from langgraph.types import Command

async def resume_graph(graph, thread_id: str, decision: dict):
    """Resume a paused graph with admin decision."""
    config = {"configurable": {"thread_id": thread_id}}
    result = await graph.ainvoke(
        Command(resume=decision),
        config=config,
    )
    return result
```

### Supabase Content CRUD
```python
# Source: Supabase Python docs + existing supabase_client.py pattern
from editorial_ai.services.supabase_client import get_supabase_client

async def save_pending_content(
    thread_id: str,
    layout_json: dict,
    title: str,
    keyword: str,
    review_summary: str | None = None,
) -> dict:
    client = await get_supabase_client()
    data = {
        "thread_id": thread_id,
        "status": "pending",
        "title": title,
        "keyword": keyword,
        "layout_json": layout_json,
        "review_summary": review_summary,
    }
    response = await client.table("editorial_contents").insert(data).execute()
    return response.data[0]

async def update_content_status(
    content_id: str,
    status: str,
    rejection_reason: str | None = None,
) -> dict:
    client = await get_supabase_client()
    data: dict = {"status": status, "updated_at": "now()"}
    if rejection_reason:
        data["rejection_reason"] = rejection_reason
    response = (
        await client.table("editorial_contents")
        .update(data)
        .eq("id", content_id)
        .execute()
    )
    return response.data[0]
```

### Testing Interrupt with MemorySaver
```python
# Source: LangGraph docs + existing test_graph.py patterns
from langgraph.checkpoint.memory import MemorySaver
from langgraph.types import Command

async def test_admin_gate_interrupt_and_resume():
    """admin_gate pauses at interrupt, resumes with Command."""
    checkpointer = MemorySaver()
    graph = build_graph(checkpointer=checkpointer)
    config = {"configurable": {"thread_id": "test-thread-1"}}

    # Run graph until interrupt
    result = await graph.ainvoke(initial_state, config=config)
    # Graph should be paused at admin_gate

    # Resume with approval
    result = await graph.ainvoke(
        Command(resume={"decision": "approved"}),
        config=config,
    )
    assert result["admin_decision"] == "approved"
    assert result["pipeline_status"] == "published"
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `NodeInterrupt` exception | `interrupt()` function | LangGraph ~0.2.x | Simpler API, cleaner node code |
| `@app.on_event("startup")` | `lifespan` context manager | FastAPI 0.93+ | Proper resource cleanup, shared state |
| Sync Supabase client | Async `acreate_client` | supabase-py 2.x | Non-blocking IO in async FastAPI |
| Manual OpenAPI spec | FastAPI auto-generated | Always | Zero-effort API documentation |

**Deprecated/outdated:**
- `NodeInterrupt`: Replaced by `interrupt()` function. Do not use.
- `@app.on_event("startup")`/`@app.on_event("shutdown")`: Deprecated in favor of `lifespan` parameter.

## Open Questions

1. **Content save timing relative to interrupt**
   - What we know: The content needs to be in Supabase for the admin to review it. The interrupt pauses the graph.
   - What's unclear: Should content be saved in a separate node BEFORE admin_gate (so it's in Supabase when admin_gate interrupts), or should admin_gate itself save it after interrupt returns?
   - Recommendation: Add a `save_content` step as part of the review-pass flow -- either as a separate node between review and admin_gate, or at the beginning of admin_gate (before interrupt, using upsert for idempotency). The latter is simpler.

2. **graph.ainvoke vs graph.astream for resume**
   - What we know: Both work for resume. `ainvoke` returns final state, `astream` yields incremental updates.
   - What's unclear: Whether the publish node after resume needs streaming.
   - Recommendation: Use `ainvoke` for V1. Streaming adds complexity with no V1 benefit since publish is a simple status update.

3. **Multiple pending contents for same thread**
   - What we know: If admin requests revision, the pipeline re-runs editorial -> review, potentially creating a new pending entry.
   - What's unclear: Should old pending entries be superseded?
   - Recommendation: On revision, mark the old content entry as `superseded` (or just use the same row with upsert on `thread_id`). Using upsert on `thread_id` is simplest.

## Sources

### Primary (HIGH confidence)
- LangGraph official docs: `interrupt()` and `Command(resume=)` pattern -- https://docs.langchain.com/oss/python/langgraph/interrupts
- FastAPI official docs: lifespan events -- https://fastapi.tiangolo.com/advanced/events/
- Supabase Python docs: insert/upsert API -- https://supabase.com/docs/reference/python/insert
- Existing codebase: `graph.py`, `state.py`, `checkpointer.py`, `supabase_client.py` -- verified directly

### Secondary (MEDIUM confidence)
- DEV.to tutorial on LangGraph interrupts with full code examples -- https://dev.to/jamesbmour/interrupts-and-commands-in-langgraph-building-human-in-the-loop-workflows-4ngl
- GitHub template: LangGraph interrupt + FastAPI architecture -- https://github.com/KirtiJha/langgraph-interrupt-workflow-template
- Multiple WebSearch results on FastAPI + LangGraph integration patterns (2025)

### Tertiary (LOW confidence)
- None -- all critical claims verified with official docs or codebase

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- all libraries already installed except FastAPI; versions verified from pyproject.toml and PyPI
- Architecture: HIGH -- interrupt/Command pattern verified against official LangGraph docs; FastAPI lifespan pattern well-documented
- Pitfalls: HIGH -- node re-execution on resume is officially documented; checkpointer requirement confirmed by codebase inspection

**Research date:** 2026-02-25
**Valid until:** 2026-03-25 (LangGraph 1.0.x is stable; FastAPI is stable)
