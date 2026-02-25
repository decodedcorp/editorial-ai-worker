---
phase: 03-curation-agent
plan: 01
subsystem: curation-service
tags: [gemini, grounding, google-search, pydantic, two-step-pattern, tenacity]

requires:
  - 01-01 (project skeleton, config.py with google_api_key)
  - 01-03 (LLM config with Settings.default_model)

provides:
  - CurationService class with curate_seed() entry point
  - CuratedTopic, CurationResult Pydantic models
  - Prompt templates for trend research and extraction
  - Two-step Gemini grounding pattern (research -> extraction)

affects:
  - 03-02 (LangGraph curation node will call CurationService.curate_seed)
  - 04-xx (editorial generation consumes CuratedTopic output)

tech-stack:
  added:
    - google-genai (native SDK, already transitive dep)
    - tenacity (already transitive dep, now used directly)
  patterns:
    - Two-step Gemini grounding (grounded search -> structured JSON extraction)
    - Retry with exponential backoff on API errors
    - Low-quality flag for degraded grounding results

key-files:
  created:
    - src/editorial_ai/models/curation.py
    - src/editorial_ai/prompts/__init__.py
    - src/editorial_ai/prompts/curation.py
    - src/editorial_ai/services/curation_service.py
    - tests/test_curation_service.py
  modified:
    - src/editorial_ai/models/__init__.py

key-decisions:
  - Native google-genai SDK (not langchain-google-genai) for grounding metadata access
  - Two-step pattern required because Gemini cannot combine grounding + structured output
  - Sequential sub-topic processing to avoid rate limits
  - Relevance threshold 0.6 (configurable) for topic filtering
  - Low-quality flag on topics with empty/poor grounding metadata

duration: ~5m
completed: 2026-02-25
---

# Phase 03 Plan 01: Curation Service Layer Summary

CurationService with two-step Gemini grounding pattern: grounded Google Search research call followed by structured JSON extraction, with tenacity retry and relevance filtering.

## Tasks Completed

| Task | Name | Commit | Key Files |
|------|------|--------|-----------|
| 1 | Curation Pydantic models and prompt templates | 0503aac | models/curation.py, prompts/curation.py |
| 2 | CurationService with two-step Gemini grounding | 86e8179 | services/curation_service.py |
| 3 | CurationService unit tests | 2316aa1 | tests/test_curation_service.py |

## What Was Built

### Pydantic Models (curation.py)
- `CuratedTopic`: keyword, trend_background, related_keywords, celebrities, brands_products, seasonality, sources, relevance_score, low_quality
- `CelebReference`, `BrandReference`: name + relevance pairs
- `GroundingSource`: url + title from Gemini search grounding
- `CurationResult`: aggregated seed_keyword, topics, total_generated, total_filtered

### Prompt Templates (prompts/curation.py)
- `build_trend_research_prompt()`: Korean+English fashion trend research prompt for grounded call
- `build_subtopic_expansion_prompt()`: Extract 3-7 sub-topic keywords as JSON array
- `build_extraction_prompt()`: Structured JSON extraction matching CuratedTopic schema

### CurationService (services/curation_service.py)
- `get_genai_client()`: Factory with API key validation
- `research_trend()`: Grounded Gemini call with source extraction from grounding_chunks
- `expand_subtopics()`: JSON extraction for sub-topic keyword expansion
- `extract_topic()`: Structured extraction with markdown fence fallback and low-quality fallback
- `curate_topic()`: Single topic pipeline (research -> extract)
- `curate_seed()`: Full entry point (research -> expand -> curate each sequentially -> filter)

### Tests (12 passing)
- Two-step pattern verification (research + extract)
- Grounding source extraction and empty grounding handling
- Subtopic parsing with cap at 7
- Markdown fence stripping fallback
- End-to-end curate_seed pipeline
- Relevance threshold filtering (< 0.6 excluded)
- Failed sub-topic resilience (skipped, not fatal)
- Retry on ClientError with tenacity

## Decisions Made

1. **Native google-genai SDK**: Direct access to `grounding_metadata.grounding_chunks` for source URLs, cleaner than langchain wrapper
2. **Two-step pattern**: Gemini 2.5 cannot combine Google Search grounding with structured JSON output in one call
3. **Sequential sub-topic processing**: Avoids rate limiting (Gemini grounding API quota)
4. **Relevance threshold 0.6**: Configurable, filters out weakly related topics
5. **Low-quality flag**: Topics with no grounding sources or parse failures are still returned but flagged

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed mypy type narrowing error**
- **Found during:** Task 2 verification
- **Issue:** Variable `topic` assigned as `CuratedTopic` then `CuratedTopic | None` in loop
- **Fix:** Used separate variable name `sub_topic` for nullable assignment
- **Commit:** 86e8179

**2. [Rule 1 - Bug] Fixed google-genai error constructors in tests**
- **Found during:** Task 3
- **Issue:** `errors.ClientError`/`errors.ServerError` require `(code, response_json)` not just message string
- **Fix:** Used `errors.ClientError(429, {"error": "Rate limited"})` and `errors.ServerError(500, {"error": "..."})`
- **Commit:** 2316aa1

**3. [Rule 1 - Bug] Fixed ruff E501 line length in prompt template**
- **Found during:** Task 3 verification
- **Issue:** Korean prompt text exceeded 100-char line limit
- **Fix:** Line continuation with backslash in f-string
- **Commit:** 2316aa1

## Next Phase Readiness

### For Plan 03-02 (LangGraph Curation Node)
- `CurationService.curate_seed(keyword) -> CurationResult` is the entry point
- `CurationResult.topics` is `list[CuratedTopic]` ready for pipeline state
- `get_genai_client()` factory creates the client
- Node should handle: convert `CuratedTopic` list to `list[dict]` for lean state
