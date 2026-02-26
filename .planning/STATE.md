# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-02-26)

**Core value:** 키워드 하나로 셀럽/상품/레퍼런스가 조합된 에디토리얼 콘텐츠가 자동 생성되고, 검수 루프를 거쳐 관리자가 승인하면 발행
**Current focus:** Milestone v1.1 complete

## Current Position

Phase: 13 of 13 (Pipeline Advanced)
Plan: 03 of 3 in phase (all complete)
Status: Phase 13 complete. v1.1 milestone complete.
Last activity: 2026-02-26 — Completed 13-03-PLAN.md (context caching)

Progress: [####################] 100% (all plans complete — v1.0 + v1.1 shipped)

## Performance Metrics

**Velocity:**
- Total plans completed: 22 (v1.0)
- Average duration: ~2.6 min
- Total execution time: ~0.95 hours

**By Phase (v1.0):**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| 1 | 3 | ~8 min | ~2.7 min |
| 2 | 2 | ~5 min | ~2.5 min |
| 3 | 2 | ~5 min | ~2.5 min |
| 4 | 3 | ~8 min | ~2.7 min |
| 5 | 3 | ~8 min | ~2.7 min |
| 6 | 3 | ~8 min | ~2.7 min |
| 7 | 3 | ~8 min | ~2.7 min |
| 8 | 3 | ~7 min | ~2.3 min |

## Accumulated Context

### Decisions

- [v1.0]: 8 phases, 22 plans completed -- all v1.0 requirements shipped
- [v1.1]: E2E 실행 검증 최우선, 관측성 백엔드 -> 대시보드 순서, ADV 기능은 파이프라인 실행 데이터 확보 후 진행
- [v1.1]: 관측성은 LangChain callbacks가 아닌 커스텀 node_wrapper 패턴 (google-genai SDK 직접 사용 때문)
- [v1.1]: 매거진 렌더러는 기존 10개 블록 컴포넌트 업그레이드 (새 아키텍처 아님)
- [09-01]: Health check returns 200 with status field (healthy/degraded/unhealthy) for diagnostic reading
- [09-01]: seed_keyword with keyword fallback for backward compatibility
- [09-01]: Env validation runs before checkpointer setup (fail-fast pattern)
- [09-02]: Text IDs (post-001, sol-001) for deterministic ON CONFLICT; matched source_node query columns exactly
- [09-03]: Non-blocking pipeline trigger via asyncio.create_task for immediate thread_id return
- [09-03]: BFF proxy pattern for API key hiding; 3s polling with 180s timeout
- [09-03]: Modal phase state machine: form -> running -> success|error
- [10-01]: model_validator(mode='before') for computed fields over @computed_field
- [10-01]: ContextVar copy-on-first-write for cross-context safety
- [10-01]: Fire-and-forget pattern for all observability I/O (try/except + log warning)
- [10-02]: 10 LLM call sites instrumented (plan listed 8, enrich_service had 2 additional)
- [10-02]: Node wrapping applied after node_overrides so test stubs also get wrapped
- [10-02]: BaseException catch for node errors to handle KeyboardInterrupt/SystemExit
- [10-03]: Logs router registered before admin at same prefix; include_io defaults true
- [11-01]: Gemini response_schema for structured DesignSpec output (not free-text parsing)
- [11-01]: design_spec_node failure returns default spec (non-critical, never crashes pipeline)
- [11-01]: DesignSpec injected into MagazineLayout at editorial_node for DB-to-frontend delivery
- [11-02]: Native <img> over next/image for magazine content (avoids remotePatterns for arbitrary external URLs)
- [11-03]: All blocks accept optional designSpec prop (forward-compatible, works without it)
- [11-03]: Drop cap uses float-left pattern with Playfair Display serif for first character
- [11-03]: Google Fonts loaded via next/font/google CSS variables (no external CDN)
- [11-04]: ContentTabs as separate client component for tab-based detail page
- [11-04]: null-to-undefined conversion at BlockRenderer boundary for designSpec prop compatibility
- [12-02]: Round grouping by detecting repeated node_name for retry visualization
- [12-02]: IO data lazy-loaded on demand (include_io=true) to avoid heavy initial page load
- [12-02]: Parallel fetch of content + logs on detail page with graceful logs failure fallback
- [12-03]: BFF list proxy enriches items server-side via Promise.all parallel log fetches (no N+1 from browser)
- [12-03]: Retry count derived from editorial node occurrence count minus one
- [12-03]: All 5 dots filled for terminal statuses; mid-pipeline stages reserved for detail page Pipeline tab
- [13-02]: Longest-match-first keyword sorting for multi-domain disambiguation in classifier
- [13-02]: DEFAULT rubric = FASHION_MAGAZINE (fashion-first pipeline)
- [13-02]: Backward compatible rubric_config=None produces original 3-criteria prompt
- [13-01]: YAML config over code constants for model mapping (easy tuning without deploys)
- [13-01]: Module-level singleton ModelRouter (initialized once, shared across requests)
- [13-01]: RoutingDecision dataclass with reason string for observability tracking
- [13-01]: revision_count >= 2 triggers Pro upgrade for editorial_content and review nodes
- [13-03]: MIN_CACHE_TOKENS=2048 with 4 chars/token estimate for cache threshold check
- [13-03]: TTL 3600s (1 hour) for cache auto-expiry after pipeline completes
- [13-03]: Singleton CacheManager via get_cache_manager() factory (lazy init)
- [13-03]: Cache keys scoped per pipeline run via thread_id (review-topics-{id}, editorial-context-{id})
- [13-03]: Fire-and-forget for all cache operations (consistent with observability pattern)

### Pending Todos

- Verify Pydantic model schemas against live Supabase tables when credentials are configured

### Blockers/Concerns

- ~~seed_keyword vs keyword 필드명 불일치~~ -- RESOLVED in 09-01
- Supabase DATABASE_URL 포트 확인 필요 (5432 session pooler, not 6543 transaction pooler)
- ~~google-genai response.usage_metadata 필드명 검증 필요~~ -- RESOLVED in 10-02 (prompt_token_count, candidates_token_count, total_token_count with getattr defaults)

## Session Continuity

Last session: 2026-02-26
Stopped at: Completed 13-03-PLAN.md (context caching). Phase 13 complete. v1.1 milestone complete.
Resume file: None
