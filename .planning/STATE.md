# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-02-20)

**Core value:** 키워드 하나로 셀럽/상품/레퍼런스가 조합된 에디토리얼 콘텐츠가 자동 생성되고, 검수 루프를 거쳐 관리자가 승인하면 발행
**Current focus:** Phase 6 in progress -- Review Agent Feedback Loop.

## Current Position

Phase: 6 of 8 (Review Agent - Feedback Loop)
Plan: 1 of 3 in phase 6
Status: In progress
Last activity: 2026-02-25 — Completed 06-01-PLAN.md

Progress: [██████████████░░░░░░░░] 14/22 (64%)

## Performance Metrics

**Velocity:**
- Total plans completed: 14
- Average duration: ~2.6m
- Total execution time: ~0.63 hours

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| 1 | 3/3 | ~9m | ~3m |
| 2 | 2/2 | ~6m | ~3m |
| 3 | 2/2 | ~7m | ~3.5m |
| 4 | 3/3 | ~8m | ~2.7m |
| 5 | 3/3 | ~6m | ~2m |
| 6 | 1/3 | ~2m | ~2m |

**Recent Trend:**
- Last 5 plans: 2m, 2m, 2m, 2m, 2m
- Trend: stable

*Updated after each plan completion*

## Accumulated Context

### Decisions

Decisions are logged in PROJECT.md Key Decisions table.
Recent decisions affecting current work:

- [Roadmap]: 8 phases derived from 17 v1 requirements, comprehensive depth
- [Roadmap]: Editorial Agent split into 2 phases (Generation+Layout / DB Tools) for focused delivery
- [Roadmap]: Admin split into Backend+HITL and Dashboard UI for API/frontend separation
- [01-01]: hatchling build backend instead of uv_build for custom package name (editorial_ai)
- [01-01]: Python 3.12+ union syntax (str | None) over Optional[str]
- [01-02]: build_graph() factory with node_overrides for testability (PregelNode wrapping prevents direct monkeypatch)
- [01-02]: Lean state principle - IDs/references only, Annotated reducers for accumulative lists only
- [01-03]: Settings-based backend switching: GOOGLE_API_KEY → Developer API, GOOGLE_GENAI_USE_VERTEXAI=true → Vertex AI
- [01-03]: Factory function pattern for per-node LLM customization (model, temperature)
- [02-01]: Pydantic models created with domain-reasonable defaults (schema discovery deferred — no Supabase credentials)
- [02-01]: MagicMock for sync client methods, AsyncMock for execute() in service tests
- [02-02]: create_checkpointer() returns async context manager; caller manages lifecycle
- [02-02]: Lean state validated at <10KB threshold via MemorySaver test
- [03-01]: Native google-genai SDK (not langchain-google-genai) for grounding metadata access
- [03-01]: Two-step Gemini pattern: grounded search -> structured JSON extraction (cannot combine)
- [03-01]: Sequential sub-topic processing to avoid rate limits
- [03-01]: Relevance threshold 0.6 (configurable) for topic filtering
- [03-02]: Real async curation_node as default in build_graph; stub kept for backward compat
- [03-02]: Sync graph tests use stub_curation override rather than converting to async
- [04-01]: Block-based schema with 10 types and discriminated union for MagazineLayout
- [04-01]: Separate EditorialContent (Gemini output) from MagazineLayout (renderer contract)
- [04-01]: list[KeyValuePair] instead of dict[str, str] for Gemini compatibility
- [04-01]: CreditEntry shared between layout and editorial models
- [04-02]: Reuse curation_service utilities (retry, strip_fences, get_client) via import
- [04-02]: response_modalities=['IMAGE', 'TEXT'] for Nano Banana mixed responses
- [04-02]: Vision parse returns list[dict] for block structure flexibility
- [04-02]: deepcopy in merge_content_into_layout for input immutability
- [04-03]: current_draft as dict|None in state (full layout JSON deferred to Supabase in Phase 7)
- [04-03]: Trend context built from all topic backgrounds + keywords, concatenated
- [04-03]: Primary keyword from first curated topic, fallback to curation_input seed
- [05-03]: Enrich node is transparent -- does not change pipeline_status (only modifies current_draft)
- [06-01]: Hybrid evaluation: Pydantic format check (deterministic) before LLM semantic evaluation
- [06-01]: LLM evaluates 3 criteria only (hallucination, fact_accuracy, content_completeness); format handled by Pydantic
- [06-01]: Overall pass requires ALL criteria to pass; any failure = overall fail
- [06-01]: Temperature 0.0 for LLM evaluation for deterministic scoring

### Pending Todos

- Verify Pydantic model schemas against live Supabase tables when credentials are configured

### Blockers/Concerns

- Supabase celeb/products 테이블 실제 스키마 확인 필요 (credentials not yet in .env.local)
- USER-SETUP required: SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY, DATABASE_URL (see .planning/phases/02-data-layer/02-USER-SETUP.md)

## Session Continuity

Last session: 2026-02-25
Stopped at: Completed 06-01-PLAN.md (Review Models, Prompt & Service)
Resume file: None
