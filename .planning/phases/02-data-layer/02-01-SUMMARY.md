---
phase: 02-data-layer
plan: 01
subsystem: data-access
tags: [supabase, pydantic, service-layer, async]
dependency-graph:
  requires: [01-01]
  provides: [supabase-client-factory, pydantic-models, service-functions]
  affects: [02-02, 05-db-tools]
tech-stack:
  added: [supabase@2.28.0, langgraph-checkpoint-postgres@3.0.4, psycopg-binary@3.3.3]
  patterns: [singleton-async-factory, pydantic-model-validate, mock-chain-pattern]
key-files:
  created:
    - src/editorial_ai/services/__init__.py
    - src/editorial_ai/services/supabase_client.py
    - src/editorial_ai/services/celeb_service.py
    - src/editorial_ai/services/product_service.py
    - src/editorial_ai/services/post_service.py
    - src/editorial_ai/models/__init__.py
    - src/editorial_ai/models/celeb.py
    - src/editorial_ai/models/product.py
    - src/editorial_ai/models/post.py
    - tests/test_services.py
  modified:
    - pyproject.toml
    - src/editorial_ai/config.py
decisions:
  - id: 02-01-01
    decision: "Pydantic models created with reasonable domain defaults since Supabase credentials not available"
    context: "No SUPABASE_URL/SUPABASE_SERVICE_ROLE_KEY in .env.local; schema discovery deferred"
  - id: 02-01-02
    decision: "MagicMock for client (sync table()), AsyncMock for execute() in tests"
    context: "supabase-py table() is sync, execute() is async; initial AsyncMock caused coroutine errors"
metrics:
  duration: ~4m
  completed: 2026-02-25
---

# Phase 02 Plan 01: Supabase Service Layer Summary

Async Supabase service layer with singleton client factory, 3 Pydantic models (Celeb/Product/Post), 6 service functions, and 12 unit tests with mocked client.

## What Was Built

### 1. Dependencies and Config Extension
- Added `supabase`, `langgraph-checkpoint-postgres`, `psycopg[binary]` to pyproject.toml
- Extended `Settings` with `supabase_url`, `supabase_service_role_key`, `database_url` (all optional with `None` default)

### 2. Supabase Client Factory
- `src/editorial_ai/services/supabase_client.py`: Singleton async factory using `acreate_client`
- Lazy initialization with module-level `_client` cache
- Clear RuntimeError if credentials are missing
- `reset_client()` helper for testing

### 3. Pydantic Models
- `Celeb`: id, name, name_en, category, profile_image_url, description, tags, timestamps
- `Product`: id, name, brand, category, price, image_url, description, product_url, tags, timestamps
- `Post`: id, title, content, status, celeb_id, thumbnail_url, tags, timestamps, published_at
- All use `ConfigDict(from_attributes=True)` for ORM compatibility
- NOTE: Schemas based on domain defaults; need verification against live Supabase

### 4. Service Functions
- `celeb_service`: `get_celeb_by_id()`, `search_celebs()`
- `product_service`: `get_product_by_id()`, `search_products()`
- `post_service`: `get_post_by_id()`, `list_posts()`
- All use PostgREST query chain with proper null handling for `maybe_single()`

### 5. Tests
- 12 unit tests with mocked Supabase client (found/not-found pairs for each service)
- 3 integration test stubs with `@pytest.mark.integration` (excluded by default)
- pytest configured with `addopts = "-m 'not integration'"`

## Decisions Made

| ID | Decision | Rationale |
|----|----------|-----------|
| 02-01-01 | Models use domain-reasonable defaults | Supabase credentials not in .env.local; schema discovery deferred to integration testing |
| 02-01-02 | MagicMock client + AsyncMock execute | supabase-py table() is sync builder, execute() is async; prevents coroutine chain errors |

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed mypy union-attr errors on maybe_single response**
- **Found during:** Task 2 verification
- **Issue:** `maybe_single().execute()` returns `SingleAPIResponse | None`, mypy flagged `.data` access
- **Fix:** Added `response is None` check before accessing `.data`
- **Files modified:** celeb_service.py, product_service.py, post_service.py

**2. [Rule 1 - Bug] Fixed AsyncMock causing coroutine chain errors in tests**
- **Found during:** Task 2 test execution
- **Issue:** `AsyncMock` client made `table()` return coroutine instead of sync builder
- **Fix:** Changed `_build_mock_client` to use `MagicMock` for client, `AsyncMock` only for `execute()`

## Verification Results

- `uv run pytest tests/ -v`: 20 passed, 3 deselected (integration)
- `uv run ruff check src/ tests/`: All checks passed
- `uv run mypy src/editorial_ai/services/ src/editorial_ai/models/ src/editorial_ai/config.py`: Success, no issues
- All import chains resolve correctly

## Next Phase Readiness

- **02-02 (Postgres Checkpointer):** Ready. `database_url` config field exists. `langgraph-checkpoint-postgres` and `psycopg[binary]` already installed.
- **Phase 5 (DB Tools):** Service functions ready to wrap as LangChain Tools.
- **Pending:** Pydantic model schemas need verification against live Supabase tables when credentials are configured.
