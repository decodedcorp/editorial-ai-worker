# Phase 9: E2E Execution Foundation - Research

**Researched:** 2026-02-26
**Domain:** Environment validation, health checks, pipeline trigger UX, sample data, field name fixes
**Confidence:** HIGH

## Summary

Phase 9 is an integration/infrastructure phase, not a new-library phase. The codebase (v1.0) already has all nodes, services, and UI wired — the work is about making the full pipeline actually run end-to-end against real Supabase + Gemini. Five concrete tasks are needed:

1. **Env validation + fail-fast** — The existing `pydantic-settings` `Settings` class has all fields optional (`str | None`). Server starts silently even with missing critical vars. Need startup validation that checks required vars and exits immediately with clear messages.
2. **Health check endpoint** — The existing `GET /health` returns a static `{"status": "ok"}`. Needs to actually probe Supabase connection, table existence, and checkpointer connectivity.
3. **`seed_keyword` vs `keyword` field name fix** — The API sends `curation_input.seed_keyword` but the curation node reads `curation_input.keyword`. This is a confirmed blocking bug.
4. **Content creation trigger UI** — The contents list page exists but has no "new content" button. Need a modal/form that calls the pipeline trigger API with keyword + options, showing node-by-node progress.
5. **Sample data SQL** — The pipeline queries `posts`, `spots`, `solutions` tables. Need seed data so the pipeline produces meaningful results on a fresh DB.

**Primary recommendation:** Fix the field name bug first (it's a one-line fix that unblocks everything), then add env validation, health check, sample data, and trigger UI in parallel.

## Standard Stack

### Core (Already Installed)
| Library | Version | Purpose | Notes |
|---------|---------|---------|-------|
| FastAPI | >=0.115 | API server, health endpoint | Already in pyproject.toml |
| pydantic-settings | >=2.8 | Env var loading, validation | Already used in config.py |
| supabase-py | >=2.28 | Supabase REST API client | Already in pyproject.toml |
| langgraph | >=1.0.9 | Pipeline graph, checkpointer | Already in pyproject.toml |
| langgraph-checkpoint-postgres | >=3.0.4 | Postgres checkpointer | Already in pyproject.toml |
| Next.js | 15.5.12 | Admin dashboard | Already in admin/package.json |
| shadcn/ui | 3.8.5 | UI components (Button, Card, etc.) | Already in admin/package.json |
| @tanstack/react-table | 8.21.x | Data table | Already used in content-table |
| lucide-react | 0.575.x | Icons | Already installed |

### Supporting (May Need Adding)
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| radix-ui/dialog | (via radix-ui 1.4.3) | Modal dialog | For trigger modal — radix-ui is already installed, dialog primitives available |

### No New Dependencies Needed

This phase requires zero new Python or Node packages. Everything needed is already installed. The shadcn CLI can generate a Dialog component from the existing radix-ui dependency.

**Installation:**
```bash
# Admin UI only — generate dialog component via shadcn
cd admin && npx shadcn@latest add dialog input label select
```

No Python package changes needed.

## Architecture Patterns

### Recommended Project Structure Changes
```
src/editorial_ai/
├── api/
│   ├── app.py              # MODIFY: add startup env validation
│   └── routes/
│       ├── health.py        # NEW: rich health check endpoint
│       └── pipeline.py      # MODIFY: fix seed_keyword, add progress SSE (optional)
├── config.py               # MODIFY: add validate_required() method
├── nodes/
│   └── curation.py          # MODIFY: fix keyword field read
scripts/
├── seed_sample_data.sql     # NEW: sample data for posts/spots/solutions
admin/src/
├── app/
│   └── api/
│       └── pipeline/
│           └── trigger/route.ts  # NEW: proxy to backend trigger
├── components/
│   └── new-content-modal.tsx     # NEW: trigger modal component
```

### Pattern 1: Fail-Fast Environment Validation
**What:** Validate required env vars at server startup, before FastAPI lifespan begins.
**When to use:** Always — prevents confusing runtime errors deep in the pipeline.
**Example:**
```python
# Source: pydantic-settings docs + FastAPI lifespan pattern
# In config.py
class Settings(BaseSettings):
    # ... existing fields ...

    def validate_required(self) -> list[str]:
        """Check required env vars and return list of missing ones."""
        required = {
            "SUPABASE_URL": self.supabase_url,
            "SUPABASE_SERVICE_ROLE_KEY": self.supabase_service_role_key,
            "DATABASE_URL": self.database_url,
        }
        # At least one LLM auth method required
        has_llm = bool(self.google_api_key) or bool(self.google_genai_use_vertexai)
        missing = [k for k, v in required.items() if not v]
        if not has_llm:
            missing.append("GOOGLE_API_KEY or GOOGLE_GENAI_USE_VERTEXAI")
        return missing

# In app.py lifespan (or before)
import sys
from editorial_ai.config import settings

def check_env():
    missing = settings.validate_required()
    if missing:
        print(f"ERROR: Missing required environment variables: {', '.join(missing)}", file=sys.stderr)
        print("See .env.example for required configuration.", file=sys.stderr)
        sys.exit(1)
```

### Pattern 2: Rich Health Check with Dependency Probing
**What:** Health endpoint that actually tests connectivity to Supabase and checkpointer.
**When to use:** Internal debugging, admin dashboard status display.
**Example:**
```python
# Source: FastAPI + supabase-py patterns
from datetime import datetime, timezone

async def _check_supabase() -> dict:
    """Probe Supabase connectivity and table existence."""
    try:
        client = await get_supabase_client()
        # Light query to verify connection
        resp = await client.table("editorial_contents").select("id", count="exact").limit(0).execute()
        return {"status": "healthy", "editorial_contents_count": resp.count}
    except Exception as e:
        return {"status": "unhealthy", "error": str(e)}

async def _check_tables(client) -> dict:
    """Verify required tables exist by attempting lightweight queries."""
    tables = ["editorial_contents", "posts", "spots", "solutions"]
    results = {}
    for table in tables:
        try:
            await client.table(table).select("id").limit(1).execute()
            results[table] = "exists"
        except Exception:
            results[table] = "missing_or_inaccessible"
    return results

async def _check_checkpointer(request) -> dict:
    """Verify checkpointer is connected."""
    try:
        cp = request.app.state.checkpointer
        # AsyncPostgresSaver has a pool; check it's alive
        # A simple get with a non-existent config verifies connectivity
        result = await cp.aget({"configurable": {"thread_id": "__health_check__"}})
        return {"status": "healthy"}  # result is None, but no error = connected
    except Exception as e:
        return {"status": "unhealthy", "error": str(e)}
```

### Pattern 3: seed_keyword Field Name Unification
**What:** The API trigger sends `seed_keyword` but curation node reads `keyword`. Both `admin_gate` and `run_pipeline.py` already handle both names.
**When to use:** Must fix for pipeline to work end-to-end.

**Current flow (BROKEN):**
```
pipeline.py: curation_input = {"seed_keyword": body.seed_keyword, "category": body.category}
curation.py: keyword = curation_input.get("keyword")  # → None!
```

**Fix options (choose ONE):**
- Option A: Change curation node to read `seed_keyword` (aligns with API/admin_gate)
- Option B: Change API to send both `seed_keyword` and `keyword`
- Option C: Change API to send `keyword` only and update admin_gate

**Recommendation: Option A** — Minimal change, aligns with the naming used everywhere else (`TriggerRequest.seed_keyword`, `CurationResult.seed_keyword`, `admin_gate` reads `seed_keyword`). The curation node docstring already says "seed keyword" but reads the wrong field.

```python
# curation.py — change line 24
# FROM:
keyword = curation_input.get("keyword")
# TO:
keyword = curation_input.get("seed_keyword") or curation_input.get("keyword")
```

The `or` fallback keeps backward compatibility with `run_pipeline.py` which sends both.

### Pattern 4: Pipeline Trigger Modal with Progress
**What:** "New Content" button on contents list → modal with keyword + options → API call → progress display.
**When to use:** E2E-04 requirement.

**UI Component Structure:**
```
contents/page.tsx
  └── NewContentButton → opens modal
      └── NewContentModal (dialog)
          ├── KeywordInput (required)
          ├── CategorySelect (optional, defaults)
          ├── Advanced options collapsible
          │   ├── Tone/Style
          │   ├── Target celeb/brand
          │   └── Layout template
          └── SubmitButton → POST /api/pipeline/trigger
              └── Progress display (polling or SSE)
```

**Progress approach:** The backend `trigger_pipeline` currently blocks until admin_gate interrupt. For the UI:
- Option A: Fire-and-forget POST, redirect to content list → poll for new item
- Option B: Use SSE/streaming from backend for real-time node progress
- **Recommendation: Option A (fire-and-forget + polling)** — simpler, the pipeline creates a content row when it reaches admin_gate, so polling the contents list works. Real-time SSE can be added in Phase 10 (observability).

**However**, the current `trigger_pipeline` endpoint is synchronous (awaits full graph execution). This means the modal will show a loading spinner for potentially 30-60+ seconds. The UI should:
1. Show a loading state with "Pipeline running..." message
2. Optionally show estimated progress based on elapsed time
3. On success, redirect to the new content detail page
4. On failure, show error message in the modal

**For node-by-node progress (decision: required):**
The simplest approach without SSE is to poll a status endpoint. Since `pipeline_status` is tracked in state, we can expose it:
- Add `GET /api/pipeline/{thread_id}/status` endpoint that reads checkpointer state
- Frontend polls every 2-3 seconds during pipeline execution
- Show step indicators: curation → source → editorial → enrich → review → awaiting approval

### Pattern 5: Sample Data SQL Structure
**What:** Seed script for posts/spots/solutions tables with realistic K-fashion data.
**When to use:** Fresh DB setup, development environment initialization.

**Tables used by the pipeline (from source code analysis):**

| Table | Queried By | Fields Used | Min Rows Needed |
|-------|-----------|-------------|-----------------|
| `posts` | source_node, curation_service | id, image_url, media_type, title, artist_name, group_name, context, view_count, trending_score, status | 15-20 |
| `spots` | source_node | id, post_id | 20-30 (linked to posts) |
| `solutions` | source_node, curation_service | id, title, thumbnail_url, metadata, link_type, original_url | 20-30 (linked to spots) |
| `editorial_contents` | content_service | Auto-created by pipeline | 0 (created by pipeline) |
| `celebs` | celeb_service | id, name, name_en, category, profile_image_url, description, tags | Optional (not used in main flow) |
| `products` | product_service | id, name, brand, category, price, image_url, description, product_url, tags | Optional (not used in main flow) |

**NOTE:** The main pipeline flow uses `posts` → `spots` → `solutions`, NOT the `celebs`/`products` tables directly. The `celeb_service` and `product_service` exist but are used by the legacy `enrich_node` (replaced by `enrich_from_posts_node`). The sample data should focus on posts/spots/solutions.

The decision says "celebs 10-15, products 15-20" but these aren't used by the active pipeline. **Recommendation:** Include them anyway for completeness and future use, but prioritize posts/spots/solutions for E2E execution.

### Anti-Patterns to Avoid
- **Don't make health check call Gemini API:** Health checks should be fast (<500ms) and free. Only check infrastructure dependencies (Supabase, Postgres).
- **Don't add WebSocket for progress:** Overkill for this phase. Polling is fine. SSE/WS can be Phase 10.
- **Don't create a separate "environments" table:** The decision says env validation at startup, not runtime DB-based config.
- **Don't change `TriggerRequest.seed_keyword` to `keyword`:** The field name `seed_keyword` is semantically correct and used in multiple places. Fix the consumer (curation node), not the API contract.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Modal dialog | Custom overlay | shadcn Dialog (already has radix-ui) | Accessibility, focus trap, escape handling |
| Form validation | Manual checks | HTML5 required + controlled state | Simple form, no need for react-hook-form |
| Env var validation | Custom parser | pydantic-settings `model_validator` | Already parses .env, just add a check method |
| Health check response | Custom format | Standard JSON `{status, checks: {...}}` | Simple enough, no library needed |
| SQL seed scripts | ORM/migration tool | Plain `.sql` files in `scripts/` | One-time seed data, not schema migration |

**Key insight:** This phase is about wiring and fixing, not building new systems. Every piece already exists — env loading (pydantic-settings), health endpoint (FastAPI), trigger API (pipeline route), UI framework (Next.js + shadcn). The work is connecting and hardening.

## Common Pitfalls

### Pitfall 1: Pipeline Timeout on Trigger
**What goes wrong:** The `trigger_pipeline` endpoint awaits `graph.ainvoke()` which runs curation → source → editorial → enrich → review → admin_gate. With real Gemini calls, this can take 30-120 seconds. HTTP clients or reverse proxies may timeout.
**Why it happens:** The endpoint was designed for dev/testing, not production UX.
**How to avoid:**
- Set appropriate timeout on the fetch call in the admin frontend (120s+)
- Consider making the trigger async (return thread_id immediately, run pipeline in background) — but this requires careful error handling and is complex. For Phase 9, keeping synchronous but with a generous timeout is acceptable.
- Show clear loading state in UI so user knows it's working.
**Warning signs:** 504 Gateway Timeout errors, "connection reset" in frontend.

### Pitfall 2: Supabase Table Schema Mismatch
**What goes wrong:** Pydantic models (Celeb, Product, Post) were defined based on "reasonable defaults" (see NOTE in celeb.py). Actual Supabase table schemas may differ.
**Why it happens:** v1.0 was built before live Supabase access was verified.
**How to avoid:**
- The sample data SQL script will implicitly define/validate the schema by INSERTing with specific columns.
- If tables don't exist in PRD, the seed script should CREATE TABLE first (or reference existing migrations).
- Health check should verify table existence before pipeline runs.
**Warning signs:** `PostgrestAPIError: relation "posts" does not exist`, Pydantic validation errors on SELECT responses.

### Pitfall 3: Health Check Blocking App Startup
**What goes wrong:** If health check logic is in the lifespan and Supabase is down, the app never starts.
**How to avoid:**
- Env validation should be in lifespan (fail-fast: no env = no start).
- Health check should be a runtime endpoint (app starts, health check returns degraded status).
- Don't put connectivity checks in lifespan; only structural checks (env vars present).
**Warning signs:** App hangs on startup when Supabase is unreachable.

### Pitfall 4: SSE/Streaming Complexity Creep
**What goes wrong:** Building real-time node progress streaming adds significant complexity (SSE endpoint, frontend EventSource, error recovery, connection management).
**Why it happens:** "Node-by-node progress" requirement sounds like it needs real-time streaming.
**How to avoid:**
- Phase 9: Use polling approach (GET status endpoint every 2-3 seconds)
- Phase 10 (observability): Add proper SSE/streaming if needed
- The pipeline already writes `pipeline_status` to state at each node, so polling the checkpointer state is straightforward.

### Pitfall 5: CORS Issues on Pipeline Trigger
**What goes wrong:** Admin frontend (Next.js on :3000) calls backend (FastAPI on :8000). Browser blocks cross-origin requests.
**How to avoid:** Already handled — `app.py` has `CORSMiddleware(allow_origins=["*"])`. But the admin frontend uses server-side API routes (`/api/...`) that proxy to the backend, so CORS isn't an issue for existing endpoints. The pipeline trigger should follow the same proxy pattern.
**Warning signs:** "CORS policy" errors in browser console.

## Code Examples

### Environment Validation (config.py enhancement)
```python
# Source: existing config.py pattern + pydantic-settings docs
import sys

class Settings(BaseSettings):
    # ... existing fields unchanged ...

    def validate_required_for_server(self) -> list[str]:
        """Return list of missing required env vars for server mode."""
        missing = []
        if not self.supabase_url:
            missing.append("SUPABASE_URL")
        if not self.supabase_service_role_key:
            missing.append("SUPABASE_SERVICE_ROLE_KEY")
        if not self.database_url:
            missing.append("DATABASE_URL")
        if not self.google_api_key and not self.google_genai_use_vertexai:
            missing.append("GOOGLE_API_KEY (or GOOGLE_GENAI_USE_VERTEXAI=true + GOOGLE_CLOUD_PROJECT)")
        return missing
```

### Health Check Endpoint (routes/health.py)
```python
# Source: FastAPI patterns
from datetime import datetime, timezone
from fastapi import APIRouter, Request

router = APIRouter()

@router.get("/health")
async def health_check(request: Request):
    checks = {}
    overall = "healthy"

    # 1. Supabase connection
    try:
        from editorial_ai.services.supabase_client import get_supabase_client
        client = await get_supabase_client()
        # Lightweight count query
        resp = await client.table("editorial_contents").select("id", count="exact").limit(0).execute()
        checks["supabase"] = {"status": "healthy", "editorial_contents": resp.count}
    except Exception as e:
        checks["supabase"] = {"status": "unhealthy", "error": str(e)}
        overall = "unhealthy"

    # 2. Required tables
    try:
        table_status = {}
        for table in ["posts", "spots", "solutions", "editorial_contents"]:
            try:
                await client.table(table).select("id").limit(1).execute()
                table_status[table] = "ok"
            except Exception:
                table_status[table] = "missing"
                overall = "degraded" if overall == "healthy" else overall
        checks["tables"] = table_status
    except Exception:
        checks["tables"] = {"status": "skipped", "reason": "supabase unhealthy"}

    # 3. Checkpointer
    try:
        cp = request.app.state.checkpointer
        await cp.aget({"configurable": {"thread_id": "__health__"}})
        checks["checkpointer"] = {"status": "healthy"}
    except Exception as e:
        checks["checkpointer"] = {"status": "unhealthy", "error": str(e)}
        overall = "unhealthy"

    return {
        "status": overall,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "checks": checks,
    }
```

### Curation Node Fix (nodes/curation.py)
```python
# Line 24 — fix field name to read seed_keyword with keyword fallback
keyword = curation_input.get("seed_keyword") or curation_input.get("keyword")
```

### Trigger Modal (admin/src/components/new-content-modal.tsx)
```tsx
// Source: shadcn Dialog + existing admin patterns
"use client";
import { useState } from "react";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { apiPost } from "@/lib/api";
import { Plus } from "lucide-react";

// Steps for progress display
const PIPELINE_STEPS = [
  { key: "curating", label: "Curation" },
  { key: "sourcing", label: "Source" },
  { key: "drafting", label: "Editorial" },
  { key: "reviewing", label: "Review" },
  { key: "awaiting_approval", label: "Ready" },
];

export function NewContentModal() {
  const [open, setOpen] = useState(false);
  const [keyword, setKeyword] = useState("");
  const [category, setCategory] = useState("fashion");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit() {
    setLoading(true);
    setError(null);
    try {
      const result = await apiPost<{ thread_id: string }>("/api/pipeline/trigger", {
        seed_keyword: keyword,
        category,
      });
      // Redirect to content list (new item will appear)
      window.location.href = "/contents";
    } catch (e) {
      setError(e instanceof Error ? e.message : "Unknown error");
    } finally {
      setLoading(false);
    }
  }

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <Button><Plus className="mr-2 size-4" /> New Content</Button>
      </DialogTrigger>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Create New Content</DialogTitle>
        </DialogHeader>
        <div className="space-y-4">
          <div>
            <Label htmlFor="keyword">Keyword</Label>
            <Input id="keyword" value={keyword} onChange={e => setKeyword(e.target.value)} placeholder="e.g. NewJeans fashion" />
          </div>
          {/* Category, tone, etc. as needed */}
          {error && <p className="text-sm text-destructive">{error}</p>}
          <Button onClick={handleSubmit} disabled={!keyword || loading}>
            {loading ? "Running Pipeline..." : "Generate"}
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  );
}
```

### Sample Data SQL Structure
```sql
-- scripts/seed_sample_data.sql
-- Idempotent: uses ON CONFLICT DO NOTHING

-- Posts: K-pop idol street fashion
INSERT INTO posts (id, image_url, media_type, title, artist_name, group_name, context, view_count, trending_score, status)
VALUES
  ('post-001', 'https://example.com/img1.jpg', 'image', 'NewJeans Hanni at Gucci SS25', 'Hanni', 'NewJeans', '2025 Milan Fashion Week', 15000, 95, 'active'),
  -- ... 15-20 rows covering 4-5 groups, multiple artists ...
ON CONFLICT (id) DO NOTHING;

-- Spots: fashion items detected in posts
INSERT INTO spots (id, post_id)
VALUES
  ('spot-001', 'post-001'),
  -- ... 20-30 rows ...
ON CONFLICT (id) DO NOTHING;

-- Solutions: identified products/brands
INSERT INTO solutions (id, title, thumbnail_url, metadata, link_type, original_url)
VALUES
  ('sol-001', 'Gucci Jackie Bag', 'https://example.com/prod1.jpg',
   '{"keywords": ["Gucci", "bag"], "qa_pairs": [{"question": "What is it?", "answer": "Gucci Jackie 1961 mini bag"}]}',
   'product', 'https://gucci.com/...'),
  -- ... 20-30 rows ...
ON CONFLICT (id) DO NOTHING;
```

### Pipeline Status Endpoint (for progress polling)
```python
# Source: LangGraph checkpointer API
@router.get("/status/{thread_id}")
async def pipeline_status(thread_id: str, graph: CompiledStateGraph = Depends(get_graph)):
    """Get current pipeline status for a running thread."""
    config = {"configurable": {"thread_id": thread_id}}
    state = await graph.aget_state(config)
    if state is None or state.values is None:
        raise HTTPException(status_code=404, detail="Thread not found")

    values = state.values
    return {
        "thread_id": thread_id,
        "pipeline_status": values.get("pipeline_status", "unknown"),
        "error_log": values.get("error_log", []),
        "has_draft": values.get("current_draft") is not None,
    }
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `pydantic` validators for env | `pydantic-settings` BaseSettings | pydantic v2 era | Clean env loading, `.env` file support built-in |
| Basic `/health` returning 200 | Dependency-checking health endpoints | Industry standard | Catches infra issues before user hits them |
| Full page reload for actions | Server Components + client interactivity | Next.js 13+ App Router | Admin already uses this pattern |

**Deprecated/outdated:**
- None relevant — all current patterns are up-to-date.

## Open Questions

1. **Supabase table schemas for posts/spots/solutions**
   - What we know: The code queries specific columns (artist_name, group_name, view_count, trending_score, status on posts; solutions join via spots). The Celeb/Product models have schema notes saying "verify against actual Supabase schema."
   - What's unclear: Exact column types, constraints, and whether tables already exist in PRD Supabase.
   - Recommendation: The seed SQL script should include `CREATE TABLE IF NOT EXISTS` with the schema matching what the code expects. Health check will verify at runtime.

2. **Pipeline execution time under real conditions**
   - What we know: The pipeline makes 4-8+ Gemini API calls (research, subtopics, extraction per topic, editorial generation, review). Each call can take 3-15 seconds.
   - What's unclear: Total wall-clock time with real Supabase + Gemini in production environment.
   - Recommendation: Set frontend timeout to 180 seconds. Add loading indicators. Consider background execution in a future phase if timing is unacceptable.

3. **TriggerRequest extended fields**
   - What we know: Decision says "keyword + advanced options (category, tone/style, target celeb/brand, layout template)."
   - What's unclear: How these advanced options flow through the pipeline — curation_input currently only passes seed_keyword + category. Tone/style/target celeb aren't consumed by any node.
   - Recommendation: Add the fields to TriggerRequest and curation_input, but they'll be informational/prompt-injection only for now. The curation prompt can be enhanced to use them.

## Sources

### Primary (HIGH confidence)
- **Codebase analysis** — Full read of all source files in `src/editorial_ai/`, `admin/src/`, `supabase/migrations/`, `scripts/`, `tests/`
- **pyproject.toml** — Verified all dependencies and versions
- **Existing patterns** — Config, API routes, services, admin components all examined

### Secondary (MEDIUM confidence)
- **pydantic-settings** — Env validation pattern well-documented, verified against existing config.py usage
- **FastAPI health check patterns** — Standard industry practice, no special library needed
- **shadcn/ui Dialog** — Confirmed radix-ui already installed in admin/package.json

### Tertiary (LOW confidence)
- **Pipeline execution timing** — Estimated based on typical Gemini API latency, not measured in this environment
- **Supabase PRD table schemas** — Cannot verify without credentials, working from code's assumptions

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — no new libraries, everything already installed
- Architecture: HIGH — extending existing patterns (FastAPI routes, Next.js components, pydantic-settings)
- Field name fix: HIGH — confirmed by reading both source and consumer code
- Sample data: MEDIUM — table schemas inferred from code queries, not verified against live DB
- Trigger UX: MEDIUM — progress polling approach is sound but execution timing is uncertain

**Research date:** 2026-02-26
**Valid until:** 2026-03-28 (stable — infrastructure/integration work, no fast-moving dependencies)
