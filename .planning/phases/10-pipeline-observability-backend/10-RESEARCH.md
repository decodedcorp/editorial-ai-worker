# Phase 10: Pipeline Observability Backend - Research

**Researched:** 2026-02-26
**Domain:** Pipeline instrumentation, metrics collection, local file storage, REST API
**Confidence:** HIGH

## Summary

This phase adds observability to the editorial pipeline by wrapping each LangGraph node with a decorator that captures execution metrics (duration, token usage, model info, input/output state) and writes them to local JSONL files. A new API endpoint serves these logs for a given content.

The approach is straightforward: the `google-genai` SDK (v1.64.0) already exposes `response.usage_metadata` with `prompt_token_count`, `candidates_token_count`, and `total_token_count` on every `GenerateContentResponse`. The challenge is that LLM calls happen inside service classes (CurationService, EditorialService, ReviewService), not in node functions directly. The node_wrapper decorator must capture timing and state at the node level, while token metrics must be collected from within the service layer's SDK calls.

**Primary recommendation:** Use a two-layer approach: (1) node_wrapper decorator for timing + state capture at node boundaries, (2) a thread-local/context-var token collector that service methods populate after each `generate_content` call. JSONL file per `thread_id` in a `data/logs/` directory. API reads and aggregates from files.

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| google-genai | 1.64.0 | Already in use; `response.usage_metadata` provides token counts | Direct SDK, no additional deps |
| stdlib `time` | - | `time.perf_counter()` for high-resolution timing | No external dep needed |
| stdlib `json` | - | JSONL serialization | No external dep needed |
| stdlib `contextvars` | - | Thread-safe token accumulation across async calls | Python 3.12 stdlib, async-safe |
| stdlib `pathlib` | - | File path management for log directory | Python stdlib |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| pydantic | 2.12.5+ | Schema for log entries (NodeRunLog model) | Type safety for log data structure |
| fastapi | 0.115.0+ | New endpoint GET /api/contents/{id}/logs | Already the API framework |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| JSONL files | SQLite | More query power, but adds dependency and complexity for simple append-read pattern |
| contextvars | Passing collector through function args | Would require changing all service method signatures; contextvars is cleaner |
| Per-thread_id files | Single global log file | Per-thread_id makes API reads O(1) file lookup vs scanning; cleaner separation |

**Installation:** No new packages needed. Everything uses existing dependencies + Python stdlib.

## Architecture Patterns

### Recommended Project Structure
```
src/editorial_ai/
├── observability/
│   ├── __init__.py
│   ├── collector.py      # TokenCollector context var + accumulation helpers
│   ├── node_wrapper.py   # Decorator that wraps node functions
│   ├── models.py         # Pydantic models: NodeRunLog, PipelineRunSummary
│   └── storage.py        # JSONL file read/write operations
├── api/
│   └── routes/
│       └── admin.py      # Extended: GET /api/contents/{id}/logs endpoint
data/
└── logs/                  # JSONL log files (gitignored)
    └── {thread_id}.jsonl  # One file per pipeline run
```

### Pattern 1: Node Wrapper Decorator
**What:** A decorator applied in `build_graph()` that wraps each node function to capture before/after state, timing, and accumulated tokens.
**When to use:** Applied to all 7 nodes at graph build time.
**Example:**
```python
# Source: Codebase analysis of graph.py build_graph()
import time
import uuid
from functools import wraps
from editorial_ai.observability.collector import reset_token_collector, get_collected_tokens
from editorial_ai.observability.storage import append_node_log

def node_wrapper(node_name: str, node_fn):
    """Wrap a node function with observability instrumentation."""
    @wraps(node_fn)
    async def wrapped(state):
        run_id = str(uuid.uuid4())
        input_snapshot = dict(state)  # shallow copy of input state
        reset_token_collector()

        start = time.perf_counter()
        error_info = None
        output = {}
        try:
            # Handle both sync and async node functions
            if asyncio.iscoroutinefunction(node_fn):
                output = await node_fn(state)
            else:
                output = node_fn(state)
            status = "success"
        except Exception as e:
            status = "error"
            error_info = {"type": type(e).__name__, "message": str(e)}
            raise
        finally:
            duration_ms = (time.perf_counter() - start) * 1000
            tokens = get_collected_tokens()
            thread_id = state.get("thread_id") or "unknown"

            try:
                append_node_log(
                    thread_id=thread_id,
                    node_name=node_name,
                    duration_ms=duration_ms,
                    status=status,
                    tokens=tokens,
                    input_state=input_snapshot,
                    output_state=output,
                    error_info=error_info,
                )
            except Exception:
                pass  # fire-and-forget

        return output
    return wrapped
```

### Pattern 2: Token Collector via ContextVar
**What:** A `contextvars.ContextVar` that accumulates token usage from multiple SDK calls within a single node execution.
**When to use:** Set/reset at node boundaries by the wrapper; appended to by service layer after each `generate_content` call.
**Example:**
```python
# Source: Python stdlib contextvars + google-genai SDK types
from contextvars import ContextVar
from dataclasses import dataclass, field

@dataclass
class TokenUsage:
    prompt_tokens: int = 0
    candidates_tokens: int = 0
    total_tokens: int = 0
    model_name: str = ""
    call_count: int = 0

_token_collector: ContextVar[list[TokenUsage]] = ContextVar("token_collector", default=[])

def reset_token_collector():
    _token_collector.set([])

def record_token_usage(response, model_name: str = ""):
    """Extract token usage from a google-genai GenerateContentResponse."""
    usage = response.usage_metadata
    if usage is None:
        return
    entry = TokenUsage(
        prompt_tokens=usage.prompt_token_count or 0,
        candidates_tokens=usage.candidates_token_count or 0,
        total_tokens=usage.total_token_count or 0,
        model_name=model_name,
        call_count=1,
    )
    _token_collector.get().append(entry)

def get_collected_tokens() -> dict:
    """Aggregate all token usage entries from this context."""
    entries = _token_collector.get()
    if not entries:
        return {"prompt_tokens": 0, "candidates_tokens": 0, "total_tokens": 0, "calls": 0}
    return {
        "prompt_tokens": sum(e.prompt_tokens for e in entries),
        "candidates_tokens": sum(e.candidates_tokens for e in entries),
        "total_tokens": sum(e.total_tokens for e in entries),
        "calls": len(entries),
        "model": entries[0].model_name if entries else "",
        "details": [
            {"prompt": e.prompt_tokens, "candidates": e.candidates_tokens, "model": e.model_name}
            for e in entries
        ],
    }
```

### Pattern 3: JSONL Storage
**What:** Each pipeline run (identified by thread_id) gets one `.jsonl` file. Each line is one node execution log.
**When to use:** All log writes (append) and reads (for API).
**Example:**
```python
# JSONL format - one line per node execution
# File: data/logs/{thread_id}.jsonl
{"node": "curation", "status": "success", "duration_ms": 3421.5, "tokens": {"prompt_tokens": 523, "candidates_tokens": 1204, "total_tokens": 1727, "calls": 2, "model": "gemini-2.5-flash"}, "started_at": "2026-02-26T10:00:00Z", "input_state": {...}, "output_state": {...}}
{"node": "source", "status": "success", "duration_ms": 892.1, "tokens": {"prompt_tokens": 0, "candidates_tokens": 0, "total_tokens": 0, "calls": 0}, ...}
```

### Pattern 4: Integration Point in build_graph()
**What:** Apply node_wrapper to all nodes inside `build_graph()` to avoid modifying individual node files.
**When to use:** Single integration point for observability.
**Example:**
```python
# In graph.py build_graph()
from editorial_ai.observability.node_wrapper import node_wrapper

def build_graph(*, node_overrides=None, checkpointer=None, enable_observability=True):
    nodes = { ... }  # existing node dict
    if node_overrides:
        nodes.update(node_overrides)

    # Wrap nodes with observability
    if enable_observability:
        nodes = {name: node_wrapper(name, fn) for name, fn in nodes.items()}

    builder = StateGraph(EditorialPipelineState)
    for name, fn in nodes.items():
        builder.add_node(name, fn)
    # ... rest unchanged
```

### Anti-Patterns to Avoid
- **Modifying each node file directly:** Adding timing/logging code to each of the 7 node files creates duplication and makes the observability concern interleaved with business logic. Use the wrapper pattern instead.
- **Storing logs in EditorialPipelineState:** The context explicitly says "관측성 데이터가 EditorialPipelineState가 아닌 별도 저장소에 저장." Adding fields to state would bloat checkpoints and couple observability to pipeline logic.
- **Synchronous file writes blocking the pipeline:** Always wrap file I/O in try/except and never let it propagate failures (fire-and-forget).
- **Single monolithic log file:** Would require scanning/filtering for specific thread_id on API reads. Per-thread_id files give O(1) lookup.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Token counting | Manual prompt character counting | `response.usage_metadata.prompt_token_count` | SDK already provides exact server-side token counts |
| Async context propagation | Global variables or passing through args | `contextvars.ContextVar` | Async-safe, zero overhead, designed for this exact use case |
| JSON serialization of Pydantic models | Custom dict building | `model.model_dump(mode="json")` for state snapshots | Handles datetime, UUID, nested models automatically |
| High-resolution timing | `datetime.now()` arithmetic | `time.perf_counter()` | Monotonic clock, microsecond precision, not affected by system clock changes |

**Key insight:** The google-genai SDK already provides detailed usage metadata on every response. The main engineering work is plumbing it from the service layer to the storage layer, not computing metrics.

## Common Pitfalls

### Pitfall 1: ContextVar Not Reset Between Nodes
**What goes wrong:** Token usage from node A leaks into node B's metrics.
**Why it happens:** ContextVar persists across await points in the same task. If not reset, the collector accumulates across nodes.
**How to avoid:** Always call `reset_token_collector()` at the START of node_wrapper, before the node function runs.
**Warning signs:** Token counts for later nodes are suspiciously high; curation tokens appear in source node metrics.

### Pitfall 2: State Snapshot Serialization Errors
**What goes wrong:** `json.dumps()` fails on state values containing non-serializable types (bytes from image generation, Pydantic models, etc.).
**Why it happens:** `EditorialPipelineState` can contain complex nested dicts with varied types. The editorial service generates image bytes.
**How to avoid:** Use a custom JSON encoder that handles bytes (base64 or skip), datetime, UUID, and falls back to `str()` for unknown types. Or truncate/summarize large values.
**Warning signs:** Log files have missing entries; fire-and-forget silently drops logs.

### Pitfall 3: Sync vs Async Node Functions
**What goes wrong:** The wrapper calls `await` on a sync function and gets TypeError.
**Why it happens:** Some nodes (stubs, enrich) may be sync; others (curation, editorial, review, admin_gate) are async.
**How to avoid:** Check `asyncio.iscoroutinefunction(node_fn)` in the wrapper and handle both cases.
**Warning signs:** TypeError in tests when using stub nodes with the wrapper.

### Pitfall 4: File I/O Race Conditions
**What goes wrong:** Concurrent writes to the same JSONL file produce corrupted lines.
**Why it happens:** Multiple asyncio tasks could theoretically write to the same thread_id log (unlikely but possible with admin resume).
**How to avoid:** Use `asyncio.Lock` per thread_id, or rely on the fact that node execution within a single graph run is sequential (LangGraph guarantee). For safety, use `fcntl.flock` or write-then-rename.
**Warning signs:** Malformed JSON lines in log files.

### Pitfall 5: Log Files Growing Without Bounds
**What goes wrong:** Log directory accumulates unbounded data over time.
**Why it happens:** No cleanup mechanism for old log files.
**How to avoid:** Document this as a future concern. For Phase 10, acceptable since it's local dev. Can add cleanup in Phase 12 or later.
**Warning signs:** Disk usage growing over weeks of development/testing.

### Pitfall 6: record_token_usage Not Called in Service Layer
**What goes wrong:** Token metrics show 0 for nodes that make LLM calls.
**Why it happens:** The service methods (CurationService, EditorialService, ReviewService) need to call `record_token_usage(response)` after each `generate_content` call, but this requires modifying service code.
**How to avoid:** Identify all `generate_content` call sites and add `record_token_usage()` after each one. There are approximately 8-10 call sites across the three services.
**Warning signs:** All token counts are 0 despite successful LLM calls.

## Code Examples

### Example 1: Extracting Token Usage from google-genai Response
```python
# Source: Verified from google-genai SDK v1.64.0 types.py (lines 6692-6727)
# GenerateContentResponse.usage_metadata has these fields:
#   - prompt_token_count: Optional[int]
#   - candidates_token_count: Optional[int]
#   - total_token_count: Optional[int]
#   - thoughts_token_count: Optional[int]  # for thinking models
#   - cached_content_token_count: Optional[int]

response = await client.aio.models.generate_content(...)
if response.usage_metadata:
    print(f"Input tokens: {response.usage_metadata.prompt_token_count}")
    print(f"Output tokens: {response.usage_metadata.candidates_token_count}")
    print(f"Total tokens: {response.usage_metadata.total_token_count}")
```

### Example 2: JSONL Append and Read
```python
import json
from pathlib import Path

LOG_DIR = Path("data/logs")

def append_node_log(thread_id: str, **log_data) -> None:
    """Append a single node log entry to the thread's JSONL file."""
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    log_file = LOG_DIR / f"{thread_id}.jsonl"
    line = json.dumps(log_data, default=str, ensure_ascii=False)
    with open(log_file, "a", encoding="utf-8") as f:
        f.write(line + "\n")

def read_node_logs(thread_id: str) -> list[dict]:
    """Read all node log entries for a thread."""
    log_file = LOG_DIR / f"{thread_id}.jsonl"
    if not log_file.exists():
        return []
    logs = []
    with open(log_file, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                logs.append(json.loads(line))
    return logs
```

### Example 3: API Endpoint Response Shape
```python
# GET /api/contents/{id}/logs response
{
    "content_id": "uuid-here",
    "thread_id": "thread-uuid",
    "runs": [
        {
            "node": "curation",
            "status": "success",
            "duration_ms": 3421.5,
            "started_at": "2026-02-26T10:00:00.000Z",
            "tokens": {
                "prompt_tokens": 523,
                "candidates_tokens": 1204,
                "total_tokens": 1727,
                "calls": 2,
                "model": "gemini-2.5-flash"
            },
            # IO data included by default (can be large)
            "input_state": { ... },
            "output_state": { ... }
        },
        # ... more nodes
    ],
    "summary": {
        "total_duration_ms": 45230.0,
        "total_tokens": 12450,
        "total_prompt_tokens": 4200,
        "total_candidates_tokens": 8250,
        "node_count": 7,
        "status": "completed",  # or "running", "failed"
        "estimated_cost_usd": 0.0045  # calculated at API response time
    }
}
```

### Example 4: Service Layer Integration Point
```python
# In CurationService.research_trend() - add after generate_content call:
from editorial_ai.observability.collector import record_token_usage

response = await self.client.aio.models.generate_content(
    model=self.model,
    contents=...,
    config=...,
)
record_token_usage(response, model_name=self.model)  # <-- ADD THIS
```

## Discretion Recommendations

### Error Logging Level
**Recommendation:** Store error type + message + first 5 lines of traceback. Full traceback is valuable for debugging but the first 5 lines usually contain the root cause. This avoids massive log entries from deeply nested async tracebacks.

### Cost Calculation Timing
**Recommendation:** Calculate at API response time, not at storage time. Reasons:
1. Pricing can change; recalculation uses current rates
2. Keeps storage format simple (just raw token counts)
3. Cost is a derived metric, not a primary measurement
4. A simple pricing dict in code (`{"gemini-2.5-flash": {"input": 0.15/1M, "output": 0.60/1M}}`) is easy to maintain

### Local File Format and Directory Structure
**Recommendation:** JSONL (one JSON object per line) in `data/logs/{thread_id}.jsonl`.
- JSONL over JSON: append-friendly (no need to read-modify-write), streaming-parseable
- Per-thread_id file: direct O(1) lookup for API reads, natural partitioning
- `data/logs/` directory: separate from `src/`, easy to gitignore, follows data directory convention

### IO Data API Return Strategy
**Recommendation:** Include IO data by default in the response, with an optional `?include_io=false` query parameter to exclude it. Rationale:
- Phase 12 dashboard will need IO data for debugging views
- The primary consumer is a developer debugging a pipeline run
- Large payloads are acceptable for a detail/debug endpoint
- Query param gives the dashboard flexibility to skip IO when showing overview

### Empty/Running Log API Response
**Recommendation:**
- No log file exists: Return `{"runs": [], "summary": null}` with 200 (not 404)
- Pipeline still running: Return partial logs (whatever has been written so far) with `"summary": {"status": "running"}`
- This works naturally with JSONL append: new lines appear as nodes complete

### Run/Attempt Identification
**Recommendation:** Use the existing `thread_id` as the primary run identifier. For the review retry loop (editorial -> review cycles), each node execution within the same thread_id is a separate log entry with a timestamp. The sequence can be reconstructed from timestamps.

For distinguishing "same content, new run" (e.g., after rejection + re-trigger), the new trigger generates a new `thread_id`, so runs are naturally separate.

No need for an additional `run_id` or `attempt_id` field -- the combination of `thread_id` + `node_name` + `started_at` is unique.

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| LangChain callbacks | Custom instrumentation | N/A (this project uses google-genai directly) | Cannot use LangChain's built-in callback system; need custom wrapper |
| OpenTelemetry for all observability | Lightweight custom for simple pipelines | N/A | OTel is overkill for a 7-node pipeline with local file storage |

**Deprecated/outdated:**
- LangChain callbacks: Not applicable because the project uses `google-genai` SDK directly, not through LangChain model wrappers for the actual LLM calls. The `llm.py` file creates `ChatGoogleGenerativeAI` but the services use `genai.Client` directly.

## Open Questions

1. **Large state snapshots**
   - What we know: `current_draft` can contain a full MagazineLayout JSON (potentially large with image URLs, paragraphs, etc.). `enriched_contexts` can contain 15 post contexts with solutions.
   - What's unclear: How large these typically are in practice. Could be 50KB-200KB per node log entry.
   - Recommendation: Store full state by default. If file sizes become problematic, add truncation later. For Phase 10 (backend only, no dashboard), full data is more useful for debugging.

2. **Gemini image generation response token metadata**
   - What we know: The Nano Banana image generation call returns image bytes, not text. It's unclear whether `usage_metadata` is populated for image generation responses.
   - What's unclear: Whether `response.usage_metadata` contains meaningful token counts for `response_modalities=["IMAGE", "TEXT"]` calls.
   - Recommendation: Still call `record_token_usage()` after image generation; if usage_metadata is None, the collector gracefully handles it (0 tokens). This can be verified during implementation.

## Sources

### Primary (HIGH confidence)
- `google/genai/types.py` v1.64.0 (local SDK source) - Verified `GenerateContentResponse.usage_metadata` field structure with exact field names: `prompt_token_count`, `candidates_token_count`, `total_token_count`, `thoughts_token_count`
- Codebase analysis of all 7 node files, 3 service files, graph.py, state.py, API routes - Mapped all LLM call sites and data flow
- Python 3.12 stdlib `contextvars` documentation - ContextVar is async-safe and task-scoped

### Secondary (MEDIUM confidence)
- JSONL format best practices - Widely used for append-only log storage (used by NDJSON, JSON Lines spec)
- Fire-and-forget observability pattern - Standard practice in production systems to prevent observability from affecting reliability

### Tertiary (LOW confidence)
- Gemini image generation token metadata availability - Not verified whether usage_metadata is populated for image generation calls

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - All tools are stdlib or already in the project
- Architecture: HIGH - Based on direct codebase analysis; patterns are well-established
- Pitfalls: HIGH - Identified from actual code analysis (sync/async mix, state serialization, ContextVar lifecycle)

**LLM call sites requiring `record_token_usage()` injection:**
1. `CurationService.research_trend()` - 1 call
2. `CurationService.expand_subtopics()` - 1 call
3. `CurationService.extract_topic()` - 1 call
4. `EditorialService.generate_content()` - 1 call
5. `EditorialService.generate_layout_image()` - 1 call
6. `EditorialService.parse_layout_image()` - 1 call
7. `EditorialService.repair_output()` - 1 call (inside retry loop)
8. `ReviewService.evaluate_with_llm()` - 1 call

**Nodes with LLM calls (need token collection):**
- curation (calls CurationService: 3+ LLM calls per invocation)
- editorial (calls EditorialService: 2-4 LLM calls per invocation)
- review (calls ReviewService: 1 LLM call per invocation)

**Nodes without LLM calls (timing + IO only):**
- source (Supabase queries only)
- enrich (pure data transformation)
- admin_gate (interrupt + Supabase upsert)
- publish (Supabase update)

**Research date:** 2026-02-26
**Valid until:** 2026-03-26 (stable domain, no fast-moving dependencies)
