---
phase: 13-pipeline-advanced
plan: 01
subsystem: api
tags: [gemini, model-routing, yaml, cost-optimization, flash-lite, pro]

# Dependency graph
requires:
  - phase: 10-observability-backend
    provides: "TokenUsage model and record_token_usage collector"
  - phase: 09-e2e-execution-foundation
    provides: "All 5 services with LLM call sites"
provides:
  - "ModelRouter singleton with YAML config-driven Gemini model selection"
  - "routing_config.yaml mapping 10 nodes to Flash-Lite/Flash/Pro tiers"
  - "TokenUsage.routing_reason field for cost analysis"
  - "Automatic Pro upgrade on revision_count >= 2 for editorial_content and review"
affects: [13-pipeline-advanced]

# Tech tracking
tech-stack:
  added: [pyyaml]
  patterns: ["Config-driven model routing via YAML + singleton pattern", "Routing decision dataclass with reason tracking"]

key-files:
  created:
    - src/editorial_ai/routing/__init__.py
    - src/editorial_ai/routing/model_router.py
    - src/editorial_ai/routing/routing_config.yaml
    - tests/test_model_router.py
  modified:
    - pyproject.toml
    - src/editorial_ai/observability/models.py
    - src/editorial_ai/observability/collector.py
    - src/editorial_ai/services/curation_service.py
    - src/editorial_ai/services/editorial_service.py
    - src/editorial_ai/services/review_service.py
    - src/editorial_ai/services/enrich_service.py
    - src/editorial_ai/services/design_spec_service.py
    - src/editorial_ai/nodes/editorial.py

key-decisions:
  - "YAML config over code constants for model mapping (easy tuning without deploys)"
  - "Module-level singleton for ModelRouter (initialized once, shared across requests)"
  - "RoutingDecision dataclass carries both model name and reason string for observability"
  - "revision_count >= 2 as Pro upgrade threshold (matches existing MAX_REVISIONS=3 escalation)"

patterns-established:
  - "get_model_router().resolve(node_name, revision_count=N) pattern for all LLM calls"
  - "routing_reason propagated through record_token_usage to TokenUsage model"

# Metrics
duration: 11min
completed: 2026-02-26
---

# Phase 13 Plan 01: Model Router Summary

**Config-driven Gemini model router mapping 10 pipeline nodes to Flash-Lite/Flash/Pro tiers with YAML config and automatic Pro upgrade on retries**

## Performance

- **Duration:** 11 min
- **Started:** 2026-02-26T09:31:38Z
- **Completed:** 2026-02-26T09:42:19Z
- **Tasks:** 2
- **Files modified:** 13

## Accomplishments
- ModelRouter with YAML config resolves node names to Gemini model tiers (Flash-Lite for 5 simple tasks, Flash for 4 complex tasks, Pro on retry upgrade)
- All 10+ LLM call sites across 5 services wired to use router-resolved models instead of hardcoded settings
- TokenUsage.routing_reason field enables cost analysis per routing decision
- 8 unit tests covering resolve, upgrade conditions, fallback, and custom config

## Task Commits

Each task was committed atomically:

1. **Task 1: Install PyYAML + ModelRouter + YAML config** - `a025d2e` (feat)
2. **Task 2: Extend observability + wire all services to use router** - `6a0f889` (feat)

## Files Created/Modified
- `src/editorial_ai/routing/__init__.py` - Package exports for ModelRouter and get_model_router
- `src/editorial_ai/routing/model_router.py` - ModelRouter class with resolve() method and singleton
- `src/editorial_ai/routing/routing_config.yaml` - YAML config mapping 10 nodes to Gemini models
- `src/editorial_ai/observability/models.py` - TokenUsage.routing_reason field
- `src/editorial_ai/observability/collector.py` - record_token_usage routing_reason parameter
- `src/editorial_ai/services/curation_service.py` - 3 methods use router (research, subtopics, extract)
- `src/editorial_ai/services/editorial_service.py` - 3 methods use router (content, layout_parse, repair)
- `src/editorial_ai/services/review_service.py` - evaluate_with_llm uses router with revision_count
- `src/editorial_ai/services/enrich_service.py` - 2 functions use router (expand_keywords, regenerate)
- `src/editorial_ai/services/design_spec_service.py` - generate_spec uses router
- `src/editorial_ai/nodes/editorial.py` - Passes revision_count to create_editorial
- `tests/test_model_router.py` - 8 unit tests for ModelRouter

## Decisions Made
- YAML config over code constants for model mapping (easy tuning without deploys)
- Module-level singleton for ModelRouter (initialized once, shared across requests)
- RoutingDecision dataclass carries both model name and reason string for observability
- revision_count >= 2 as Pro upgrade threshold (matches existing MAX_REVISIONS=3 escalation)

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Model router is wired and tested, ready for 13-02 (A/B testing) and 13-03 (cost dashboard)
- routing_config.yaml can be tuned without code changes
- routing_reason in TokenUsage enables cost analysis queries

---
*Phase: 13-pipeline-advanced*
*Completed: 2026-02-26*
