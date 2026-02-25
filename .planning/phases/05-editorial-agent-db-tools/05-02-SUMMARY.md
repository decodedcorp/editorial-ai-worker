---
phase: 05-editorial-agent-db-tools
plan: 02
subsystem: services
tags: [enrichment, gemini, keyword-expansion, layout-rebuild, orchestration]

dependency_graph:
  requires: [05-01]
  provides: [enrich_editorial_content, expand_keywords, rebuild_layout_with_db_data]
  affects: [05-03]

tech_stack:
  added: []
  patterns: [keyword-expansion-via-gemini, layout-rebuild-with-db-ids, graceful-passthrough, content-extraction-from-layout]

file_tracking:
  key_files:
    created:
      - src/editorial_ai/services/enrich_service.py
      - tests/test_enrich_service.py
    modified: []

decisions: []

metrics:
  duration: ~2m
  completed: 2026-02-25
---

# Phase 05 Plan 02: Enrich Service Orchestration Summary

**One-liner:** Full enrichment orchestration pipeline: keyword expansion via Gemini, multi-column DB search, content re-generation with real celeb/product data, and layout rebuild with actual DB IDs.

## What Was Done

### Task 1: Create enrich_service.py with full orchestration logic
Created `src/editorial_ai/services/enrich_service.py` (229 lines) with 6 public functions plus 1 internal helper:

- `extract_celeb_names(layout)`: Extracts celeb names from CelebFeatureBlock blocks
- `extract_product_names(layout)`: Extracts product names from ProductShowcaseBlock blocks
- `expand_keywords(client, keyword)`: Gemini keyword expansion into fashion-domain search terms with JSON parsing and graceful degradation on parse errors
- `regenerate_with_enrichment(client, original, celebs, products, keyword)`: Re-generates EditorialContent with real DB celeb/product data as context; falls back to original on failure
- `rebuild_layout_with_db_data(layout, enriched_content, celebs, products)`: Rebuilds layout blocks with real DB IDs via case-insensitive name matching; uses deepcopy for input immutability
- `enrich_editorial_content(layout)`: Top-level orchestrator that coordinates the full pipeline with graceful passthrough when no DB results are found
- `_extract_content_from_layout(layout)`: Internal helper that reconstructs EditorialContent from existing layout blocks for re-generation context

### Task 2: Add unit tests for enrich_service
Created `tests/test_enrich_service.py` (266 lines) with 9 tests covering:
- Extraction of celeb/product names from layout blocks (3 tests)
- Keyword expansion success and parse error graceful degradation (2 tests)
- Layout rebuild with DB IDs and input immutability preservation (2 tests)
- Full orchestration: empty DB results passthrough and successful enrichment flow (2 tests)

All external dependencies (Gemini API, Supabase search) fully mocked.

## Deviations from Plan

None - plan executed exactly as written.

## Commits

| # | Hash | Message |
|---|------|---------|
| 1 | 47f02eb | feat(05-02): create enrich_service with full orchestration pipeline |
| 2 | 2b081e1 | test(05-02): add unit tests for enrich_service with mocked dependencies |

## Verification Results

- All imports succeed (`enrich_editorial_content`, `expand_keywords`, `rebuild_layout_with_db_data`)
- 9/9 tests pass in test_enrich_service.py
- 84/84 tests pass across full test suite (no regressions)

## Next Phase Readiness

Plan 05-03 can proceed: enrich_service is ready for the LangGraph enrich node integration and graph wiring.
