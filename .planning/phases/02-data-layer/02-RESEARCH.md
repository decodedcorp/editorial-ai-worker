# Phase 2: Data Layer - Research

**Researched:** 2026-02-25
**Domain:** Supabase Python SDK (REST) + LangGraph Postgres Checkpointer
**Confidence:** HIGH

## Summary

Phase 2 connects the editorial pipeline to Supabase for data access and sets up Postgres-based state persistence via LangGraph's checkpointer. Two distinct concerns exist: (1) a Supabase service layer using the `supabase` Python SDK (REST/PostgREST) for celeb, product, and post reads, and (2) an `AsyncPostgresSaver` checkpointer using `langgraph-checkpoint-postgres` with direct psycopg3 connections for graph state persistence.

The supabase-py SDK (v2.28.0) provides both sync (`create_client`) and async (`acreate_client`) clients. Service role key passed as the `key` parameter bypasses RLS automatically. The checkpointer package (v3.0.4) uses psycopg3 with `from_conn_string()` which already sets `prepare_threshold=0` and `autocommit=True`, making it compatible with Supabase's connection pooler.

Key architectural decision: the Supabase REST SDK and the checkpointer use **different connection paths**. The SDK communicates via Supabase's REST API (HTTPS), while the checkpointer needs a direct Postgres connection string (via pooler). These are independent and should be configured separately.

**Primary recommendation:** Use `supabase` SDK v2.28.x for data reads via REST API, and `langgraph-checkpoint-postgres` v3.0.x for checkpointing via Supabase's Postgres pooler (session mode, port 5432). Same Supabase DB instance for both.

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `supabase` | 2.28.0 | REST client for Supabase (celeb/product/post reads) | Official Python SDK, actively maintained, PostgREST-based |
| `langgraph-checkpoint-postgres` | 3.0.4 | AsyncPostgresSaver for graph state persistence | Official LangGraph checkpointer, psycopg3-based |
| `psycopg[binary]` | 3.x (transitive) | Postgres driver for checkpointer | Required by langgraph-checkpoint-postgres, binary wheels for easy install |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `langgraph-checkpoint` | (transitive) | Base checkpointer interfaces | Installed automatically with langgraph-checkpoint-postgres |
| `pydantic` | 2.x (existing) | Data models for service layer responses | Already in project, use for celeb/product/post models |
| `pydantic-settings` | 2.x (existing) | Settings extension for Supabase config | Extend existing `Settings` class with SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| supabase SDK (REST) | psycopg3 direct SQL | More control but loses PostgREST convenience; REST is simpler for reads |
| AsyncPostgresSaver | MemorySaver | No persistence; only for testing |
| Same Supabase DB for checkpointer | Separate Postgres instance | Extra infra cost; single DB is fine for this scale |

**Installation:**
```bash
uv add supabase langgraph-checkpoint-postgres "psycopg[binary]"
```

## Architecture Patterns

### Recommended Project Structure
```
src/editorial_ai/
├── config.py              # Extend Settings with SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY, DATABASE_URL
├── services/
│   ├── __init__.py
│   ├── supabase_client.py # Singleton async client factory
│   ├── celeb_service.py   # get_celeb_by_id, search_celebs
│   ├── product_service.py # get_product_by_id, search_products
│   └── post_service.py    # get_post_by_id, list_posts
├── models/
│   ├── __init__.py
│   ├── celeb.py           # Pydantic model matching Supabase schema
│   ├── product.py         # Pydantic model matching Supabase schema
│   └── post.py            # Pydantic model matching Supabase schema
├── checkpointer.py        # AsyncPostgresSaver factory
├── graph.py               # Extend build_graph to accept checkpointer param
├── state.py               # (unchanged from Phase 1)
└── ...
```

### Pattern 1: Supabase Client Factory (Singleton)
**What:** Create a module-level async client factory that lazily initializes the Supabase async client once.
**When to use:** Every service function that needs DB access.
**Example:**
```python
# src/editorial_ai/services/supabase_client.py
from supabase import acreate_client, AsyncClient
from editorial_ai.config import settings

_client: AsyncClient | None = None

async def get_supabase_client() -> AsyncClient:
    global _client
    if _client is None:
        _client = await acreate_client(
            settings.supabase_url,
            settings.supabase_service_role_key,
        )
    return _client
```
Source: supabase-py official docs + GitHub README

### Pattern 2: Service Layer Functions (Read-Only)
**What:** Thin async functions that wrap Supabase PostgREST queries and return Pydantic models.
**When to use:** Whenever a graph node needs to read celeb/product/post data.
**Example:**
```python
# src/editorial_ai/services/celeb_service.py
from editorial_ai.models.celeb import Celeb
from editorial_ai.services.supabase_client import get_supabase_client

async def get_celeb_by_id(celeb_id: str) -> Celeb | None:
    client = await get_supabase_client()
    response = client.table("celebs").select("*").eq("id", celeb_id).maybe_single().execute()
    return Celeb(**response.data) if response.data else None

async def search_celebs(query: str, limit: int = 10) -> list[Celeb]:
    client = await get_supabase_client()
    response = (
        client.table("celebs")
        .select("*")
        .ilike("name", f"%{query}%")
        .limit(limit)
        .execute()
    )
    return [Celeb(**row) for row in response.data]
```
Source: supabase.com/docs/reference/python/select, ilike

### Pattern 3: AsyncPostgresSaver with Supabase Pooler
**What:** Create a checkpointer factory that uses Supabase's Postgres pooler connection string.
**When to use:** Graph compilation for production (with persistence) vs testing (with MemorySaver).
**Example:**
```python
# src/editorial_ai/checkpointer.py
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from editorial_ai.config import settings

async def create_checkpointer() -> AsyncPostgresSaver:
    """Create an AsyncPostgresSaver connected to Supabase Postgres.

    Uses from_conn_string which sets autocommit=True, prepare_threshold=0,
    row_factory=dict_row automatically -- compatible with Supabase pooler.
    """
    checkpointer = AsyncPostgresSaver.from_conn_string(settings.database_url)
    # Note: from_conn_string returns an async context manager.
    # The caller must manage the lifecycle (async with).
    return checkpointer
```
Source: langgraph-checkpoint-postgres PyPI, GitHub source

### Pattern 4: Graph Compilation with Optional Checkpointer
**What:** Extend `build_graph()` to accept a `checkpointer` parameter so it can be injected at compile time.
**When to use:** Production uses AsyncPostgresSaver, tests use MemorySaver or None.
**Example:**
```python
# Modified build_graph in graph.py
from langgraph.checkpoint.base import BaseCheckpointSaver

def build_graph(
    *,
    node_overrides: dict[str, Callable[..., Any]] | None = None,
    checkpointer: BaseCheckpointSaver | None = None,
) -> CompiledStateGraph:
    # ... existing builder setup ...
    return builder.compile(checkpointer=checkpointer)
```
Source: LangGraph official docs (add-memory)

### Pattern 5: Interrupt Pattern for Admin HITL
**What:** Use `interrupt()` in admin_gate node to pause for human approval, resume with `Command(resume=...)`.
**When to use:** Phase 7 implements the full HITL, but checkpointer must be ready now to support it.
**Example:**
```python
# Future admin_gate implementation (Phase 7)
from langgraph.types import interrupt, Command

def admin_gate(state: EditorialPipelineState) -> dict:
    decision = interrupt({
        "message": "Review draft for approval",
        "draft_id": state["current_draft_id"],
    })
    return {
        "admin_decision": decision["action"],  # "approved" | "rejected" | "revision_requested"
        "admin_feedback": decision.get("feedback"),
    }

# Resume: graph.invoke(Command(resume={"action": "approved"}), config=config)
```
Source: LangGraph interrupts docs

### Anti-Patterns to Avoid
- **Fat state storage:** Never store full celeb/product/post payloads in graph state. State holds IDs only; nodes fetch data from Supabase when needed.
- **Sync client in async pipeline:** LangGraph runs async. Use `acreate_client` (not `create_client`) for the Supabase client.
- **Global compiled graph with checkpointer:** The current `graph = build_graph()` at module level cannot use an async checkpointer (needs await). Keep the module-level graph without checkpointer for testing; create checkpointer-enabled graphs in the application entrypoint.
- **Checkpointer as context manager in module scope:** `AsyncPostgresSaver.from_conn_string()` is an async context manager. It must be used within an async function, not at import time.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Postgres connection management | Custom connection pooling | `AsyncPostgresSaver.from_conn_string()` | Already handles autocommit, prepare_threshold, row_factory |
| Checkpoint table schema | Manual CREATE TABLE | `await checkpointer.setup()` | Handles migrations automatically |
| REST API to Supabase | Custom HTTP client | `supabase` SDK | PostgREST query builder with filtering, pagination |
| Data validation | Manual dict checking | Pydantic models | Type safety, serialization, schema documentation |
| Thread state management | Custom checkpoint logic | LangGraph's built-in thread_id config | Proven, tested, handles edge cases |

**Key insight:** The supabase SDK handles REST/PostgREST complexities (auth headers, pagination, filtering), and langgraph-checkpoint-postgres handles all checkpoint schema migrations. Both are actively maintained and battle-tested. Custom implementations add maintenance burden with no benefit.

## Common Pitfalls

### Pitfall 1: Supabase Pooler Mode + Prepared Statements
**What goes wrong:** psycopg3 uses prepared statements by default. Supabase transaction pooler (port 6543) does NOT support prepared statements, causing `InvalidSqlStatementName` errors.
**Why it happens:** Transaction mode shares connections between clients, so prepared statements from one client are invalid for another.
**How to avoid:** `AsyncPostgresSaver.from_conn_string()` already sets `prepare_threshold=0`. If manually creating connections, always include `prepare_threshold=0`. Use session mode pooler (port 5432) or direct connection if possible.
**Warning signs:** `psycopg.errors.InvalidSqlStatementName` errors at runtime.

### Pitfall 2: Async Context Manager Lifecycle
**What goes wrong:** `AsyncPostgresSaver.from_conn_string()` returns an async context manager. Using it outside `async with` leaks connections.
**Why it happens:** The checkpointer opens a psycopg connection that needs explicit cleanup.
**How to avoid:** Always use `async with AsyncPostgresSaver.from_conn_string(uri) as checkpointer:` or manage the lifecycle in the application's startup/shutdown.
**Warning signs:** Connection pool exhaustion, "too many connections" errors.

### Pitfall 3: Module-Level Async Initialization
**What goes wrong:** Trying to create async Supabase client or checkpointer at module import time.
**Why it happens:** `acreate_client()` and `AsyncPostgresSaver.from_conn_string()` are async; Python modules execute synchronously at import.
**How to avoid:** Use lazy initialization pattern (singleton factory) or application lifecycle hooks.
**Warning signs:** `RuntimeError: no running event loop` at import time.

### Pitfall 4: Supabase 1000-Row Default Limit
**What goes wrong:** Queries return only 1000 rows even when more exist.
**Why it happens:** Supabase/PostgREST defaults to max 1000 rows per response.
**How to avoid:** Always use `.limit()` explicitly, implement pagination with `.range(start, end)` for large datasets.
**Warning signs:** Unexpectedly truncated result sets.

### Pitfall 5: Checkpointer setup() Not Called
**What goes wrong:** First checkpoint write fails with missing table error.
**Why it happens:** The checkpoint tables (`checkpoints`, `checkpoint_blobs`, `checkpoint_writes`, `checkpoint_migrations`) don't exist until `setup()` is called.
**How to avoid:** Call `await checkpointer.setup()` once on first deployment. The method is idempotent (safe to call multiple times).
**Warning signs:** `UndefinedTable` error from Postgres.

### Pitfall 6: Testing Against Production Supabase
**What goes wrong:** Tests accidentally modify production data.
**Why it happens:** Single Supabase project (no dev/prod separation), tests using service_role key have full access.
**How to avoid:** Service layer tests must be READ-ONLY against real Supabase. Write operations must use mocks. Checkpointer tests use MemorySaver (or local SQLite/Postgres).
**Warning signs:** Missing or modified data in production Supabase.

### Pitfall 7: Supabase IPv6 Direct Connection Failure
**What goes wrong:** Direct Postgres connection fails on IPv4-only environments.
**Why it happens:** Supabase moved to IPv6-only for direct connections in 2024.
**How to avoid:** Use the pooler connection string (session mode port 5432 or transaction mode port 6543) instead of direct connection. Both pooler modes support IPv4.
**Warning signs:** Connection timeout or DNS resolution failure for `db.*.supabase.co`.

## Code Examples

### Supabase Settings Extension
```python
# Extend existing Settings in config.py
class Settings(BaseSettings):
    # ... existing LLM settings ...

    # Supabase
    supabase_url: str = Field(alias="SUPABASE_URL")
    supabase_service_role_key: str = Field(alias="SUPABASE_SERVICE_ROLE_KEY")

    # Postgres (for checkpointer - Supabase pooler connection string)
    database_url: str = Field(alias="DATABASE_URL")
```
Source: Existing Phase 1 config.py pattern

### Supabase PostgREST Query Patterns
```python
# Equality filter
response = client.table("celebs").select("*").eq("id", "some-uuid").single().execute()

# Case-insensitive pattern match
response = client.table("celebs").select("*").ilike("name", "%keyword%").limit(10).execute()

# Pagination
response = client.table("products").select("*").range(0, 49).execute()  # rows 0-49

# Relationship join (if foreign keys exist)
response = client.table("posts").select("*, celebs(name)").eq("id", post_id).execute()

# Multiple filters (AND)
response = (
    client.table("products")
    .select("*")
    .eq("category", "fashion")
    .ilike("name", "%dress%")
    .limit(20)
    .execute()
)
```
Source: supabase.com/docs/reference/python/select, ilike

### Checkpointer with Graph (Full Lifecycle)
```python
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from editorial_ai.config import settings
from editorial_ai.graph import build_graph

async def run_pipeline(input_state: dict, thread_id: str):
    async with AsyncPostgresSaver.from_conn_string(settings.database_url) as checkpointer:
        await checkpointer.setup()  # idempotent, safe to call every time

        graph = build_graph(checkpointer=checkpointer)
        config = {"configurable": {"thread_id": thread_id}}

        result = await graph.ainvoke(input_state, config=config)
        return result
```
Source: langgraph-checkpoint-postgres PyPI, LangGraph add-memory docs

### Testing with MemorySaver (No Postgres Required)
```python
from langgraph.checkpoint.memory import MemorySaver

def test_graph_with_checkpointer():
    checkpointer = MemorySaver()
    graph = build_graph(checkpointer=checkpointer)

    config = {"configurable": {"thread_id": "test-thread-1"}}
    result = graph.invoke(initial_state(), config=config)

    # Verify state was saved
    saved_state = graph.get_state(config)
    assert saved_state is not None
```
Source: LangGraph docs (MemorySaver for testing)

### Service Layer Test Pattern (Read-Only, Real Supabase)
```python
import pytest
from editorial_ai.services.celeb_service import get_celeb_by_id, search_celebs

@pytest.mark.integration
async def test_search_celebs_returns_results():
    """Read-only test against real Supabase."""
    results = await search_celebs("김", limit=5)
    assert isinstance(results, list)
    # Don't assert specific counts -- data may change
    for celeb in results:
        assert celeb.id is not None
        assert celeb.name is not None
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `langchain_postgres.PostgresSaver` | `langgraph-checkpoint-postgres` AsyncPostgresSaver | 2024 | Separate package, async-first, migration support |
| `MemorySaver` (was `InMemorySaver`) | `MemorySaver` | langgraph 0.2.x | Renamed but same functionality |
| supabase-py v1 | supabase v2.28.0 | 2024 | New API, async support via `acreate_client` |
| Supabase PgBouncer | Supavisor | 2024-2025 | New connection pooler, session mode on 5432, transaction on 6543 |
| Supabase session mode on 6543 | Deprecated (Feb 2025) | 2025-02 | Port 6543 is transaction-only now; session mode on 5432 |

**Deprecated/outdated:**
- `langchain_postgres.checkpoint.PostgresSaver`: Old location, use `langgraph.checkpoint.postgres` instead
- Supabase PgBouncer pooler: Replaced by Supavisor
- Session mode on port 6543: Deprecated since Feb 2025

## Recommendations for Claude's Discretion Items

### 1. Checkpointer DB Instance: Same Supabase DB (Recommended)
**Recommendation:** Use the same Supabase Postgres instance for both data and checkpointing.
**Reasoning:** Single Supabase project simplifies configuration. Checkpointer creates its own tables (`checkpoints`, `checkpoint_blobs`, `checkpoint_writes`, `checkpoint_migrations`) which don't conflict with existing celeb/product/post tables. The checkpointer's write load is minimal (one checkpoint per node execution).
**Confidence:** HIGH

### 2. Lean State Boundary Design
**Recommendation:** State stores only:
- IDs: `celeb_ids: list[str]`, `product_ids: list[str]`, `post_id: str | None`
- Intermediate decisions: `curated_topics`, `review_result`, `admin_decision` (small dicts/strings)
- Pipeline metadata: `pipeline_status`, `revision_count`, `error_log`

State does NOT store: full celeb profiles, product details, post content, LLM-generated text bodies. Nodes fetch these from Supabase by ID when needed.
**Confidence:** HIGH

### 3. Interrupt/Resume Scenarios
**Recommendation:** Phase 2 establishes the checkpointer infrastructure. The admin_gate HITL interrupt pattern will be implemented in Phase 7. For now, the checkpointer enables:
- Graph resumption after process restart (same thread_id)
- State inspection via `graph.get_state(config)`
- Future interrupt support without architectural changes

For error recovery, a failed node raises an exception; the checkpointer preserves the last successful state. Re-invoking with the same thread_id resumes from the last checkpoint.
**Confidence:** HIGH

### 4. Checkpointer Data Retention Policy
**Recommendation:** No auto-cleanup in Phase 2. Checkpointer data is small (lean state). Implement cleanup later if needed. Options for future:
- `checkpointer.delete_thread(thread_id)` for explicit cleanup
- Scheduled cleanup of threads older than N days (Phase 7+)
**Confidence:** MEDIUM -- exact retention depends on production volume which is unknown

### 5. thread_id Management Strategy
**Recommendation:** Use `{keyword}-{timestamp}` format for thread_id, e.g., `"spring-fashion-2026W08-1708876543"`. This provides:
- Human-readable identification
- Uniqueness via timestamp
- Easy filtering/searching by keyword
- No collision between concurrent pipeline runs

The thread_id is created by the pipeline trigger (API call or cron) and passed through the config.
**Confidence:** MEDIUM -- format may evolve as usage patterns emerge

### 6. Checkpointer Test Strategy
**Recommendation:** Three-tier testing approach:
1. **Unit tests (MemorySaver):** Test graph topology, state transitions, interrupt/resume logic. No external dependencies. Run in CI.
2. **Integration tests (real Supabase, read-only):** Test service layer reads against real Supabase. Mark with `@pytest.mark.integration`.
3. **Checkpointer integration tests (optional, local Postgres):** If needed, use a local Postgres (Docker) to test real AsyncPostgresSaver behavior. Not required for Phase 2 if MemorySaver tests cover the logic.
**Confidence:** HIGH

## Open Questions

1. **Actual Supabase table schemas**
   - What we know: Tables for celebs, products, posts exist in Supabase
   - What's unclear: Exact column names, types, relationships (foreign keys)
   - Recommendation: Query Supabase during implementation to inspect actual schemas, then create matching Pydantic models. This is a Phase 2 implementation task, not a blocker.

2. **Supabase pooler connection string format**
   - What we know: Session mode on port 5432, transaction mode on port 6543. Format is `postgres://postgres.[project-ref]:[password]@aws-0-[region].pooler.supabase.com:[port]/postgres`
   - What's unclear: Which mode is best for checkpointer (session vs transaction)
   - Recommendation: Use session mode (port 5432) for checkpointer since it supports prepared statements and maintains connection state. `from_conn_string` sets `prepare_threshold=0` anyway, so transaction mode (port 6543) would also work. Session mode is safer.

3. **Supabase acreate_client lifecycle in worker context**
   - What we know: `acreate_client` creates an async client that should be cleaned up with `client.auth.sign_out()`
   - What's unclear: Whether the worker runs as a long-lived process or per-invocation
   - Recommendation: Use singleton pattern for now; add proper lifecycle management when the deployment model is decided.

## Sources

### Primary (HIGH confidence)
- [langgraph-checkpoint-postgres PyPI](https://pypi.org/project/langgraph-checkpoint-postgres/) - v3.0.4, dependencies, code examples
- [langgraph-checkpoint-postgres GitHub source (aio.py)](https://github.com/langchain-ai/langgraph/blob/main/libs/checkpoint-postgres/langgraph/checkpoint/postgres/aio.py) - `from_conn_string` implementation, `prepare_threshold=0` verified
- [supabase PyPI](https://pypi.org/project/supabase/) - v2.28.0, installation
- [Supabase Python docs (initializing)](https://supabase.com/docs/reference/python/initializing) - create_client, acreate_client, ClientOptions
- [Supabase Python docs (select)](https://supabase.com/docs/reference/python/select) - query patterns, filtering, pagination
- [LangGraph Memory docs](https://docs.langchain.com/oss/python/langgraph/add-memory) - checkpointer compilation, thread_id, MemorySaver
- [LangGraph Interrupts docs](https://docs.langchain.com/oss/python/langgraph/interrupts) - interrupt(), Command(resume=...), HITL pattern
- [Supabase connecting to Postgres](https://supabase.com/docs/guides/database/connecting-to-postgres) - connection string formats, pooler modes

### Secondary (MEDIUM confidence)
- [Supabase API keys docs](https://supabase.com/docs/guides/api/api-keys) - service_role key bypasses RLS
- [LangGraph GitHub Discussion #2967](https://github.com/langchain-ai/langgraph/discussions/2967) - AsyncPostgresSaver + Supabase session pooler issues
- [LangGraph GitHub Issue #2755](https://github.com/langchain-ai/langgraph/issues/2755) - InvalidSqlStatementName with prepared statements
- [Supabase Supavisor docs](https://supabase.com/docs/guides/troubleshooting/supavisor-and-connection-terminology-explained-9pr_ZO) - pooler mode details, port deprecation

### Tertiary (LOW confidence)
- Various Medium articles on LangGraph + Postgres patterns (cross-verified with official docs)

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - All libraries verified via PyPI and official docs
- Architecture: HIGH - Patterns verified against official examples and existing Phase 1 codebase
- Pitfalls: HIGH - Multiple sources confirm prepared statement issues, lifecycle management, IPv6 concerns

**Research date:** 2026-02-25
**Valid until:** 2026-03-25 (30 days - stack is stable)
