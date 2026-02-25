---
phase: 05-editorial-agent-db-tools
plan: 01
subsystem: services
tags: [supabase, search, prompts, enrichment]

dependency_graph:
  requires: [02-01]
  provides: [search_celebs_multi, search_products_multi, enrich_prompts]
  affects: [05-02, 05-03]

tech_stack:
  added: []
  patterns: [multi-column-or-search, deduplication-by-id, prompt-builder]

file_tracking:
  key_files:
    created:
      - src/editorial_ai/prompts/enrich.py
    modified:
      - src/editorial_ai/services/celeb_service.py
      - src/editorial_ai/services/product_service.py
      - tests/test_services.py

decisions: []

metrics:
  duration: ~2m
  completed: 2026-02-25
---

# Phase 05 Plan 01: Multi-Column Search & Enrich Prompts Summary

**One-liner:** Multi-column OR search for celebs/products via PostgREST or_() with deduplication, plus keyword expansion and content regeneration prompt templates for the enrichment pipeline.

## What Was Done

### Task 1: Multi-column OR search functions
Added `search_celebs_multi()` and `search_products_multi()` to their respective service modules. Each function:
- Accepts a list of query strings
- Searches across multiple columns using Supabase `or_()` with PostgREST ilike syntax
- Celebs: name, name_en, description
- Products: name, brand, description
- Deduplicates results by ID preserving first occurrence order
- Returns empty list for empty query input without error

### Task 2: Enrich prompts module
Created `src/editorial_ai/prompts/enrich.py` with two prompt builder functions:
- `build_keyword_expansion_prompt(keyword)`: Instructs Gemini to expand a fashion keyword into 5-10 related Korean search terms as JSON array. Domain-constrained to fashion/celebrity/brand.
- `build_enrichment_regeneration_prompt(original_content_json, celebs_json, products_json, keyword)`: Instructs Gemini to re-generate EditorialContent by naturally incorporating real DB celeb/product data while preserving editorial quality and tone.

### Task 3: Unit tests
Added 6 new tests covering multi-column search and deduplication for both celebs and products. Created `_build_mock_client_or` helper extending existing mock pattern with `or_()` chain support. All 18 tests pass (12 existing + 6 new).

## Deviations from Plan

None - plan executed exactly as written.

## Commits

| # | Hash | Message |
|---|------|---------|
| 1 | 65beaa9 | feat(05-01): add multi-column OR search to celeb and product services |
| 2 | 042f727 | feat(05-01): create enrich prompts module for keyword expansion and content regeneration |
| 3 | cc9afd1 | test(05-01): add unit tests for multi-column search and deduplication |

## Verification Results

- All imports succeed (search_celebs_multi, search_products_multi, enrich prompts)
- 18/18 tests pass in test_services.py
- Existing functions unchanged (backward compatible)

## Next Phase Readiness

Plan 05-02 can proceed: search functions and enrich prompts are ready for the enrich_editorial node implementation.
