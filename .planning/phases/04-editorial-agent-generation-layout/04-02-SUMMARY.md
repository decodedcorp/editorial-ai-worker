---
phase: 04-editorial-agent-generation-layout
plan: 02
subsystem: services
tags: [gemini, structured-output, nano-banana, vision-ai, editorial, pipeline, repair-loop]

requires:
  - phase: 04-editorial-agent-generation-layout
    provides: MagazineLayout schema, EditorialContent model, create_default_template
  - phase: 03-curation-agent
    provides: CurationService pattern, retry_on_api_error, _strip_markdown_fences, get_genai_client
provides:
  - EditorialService with 3-step pipeline (content gen, layout image, vision parse)
  - Editorial prompt templates (content, layout image, layout parsing, output repair)
  - Output repair loop for Pydantic validation failures
  - Template fallback when Nano Banana or Vision fails
affects: [04-03, 04-04, 05-db-tools]

tech-stack:
  added: []
  patterns:
    - "3-step editorial pipeline: Gemini structured output -> Nano Banana image -> Vision parse"
    - "Output repair loop: _validate_with_repair retries Gemini on Pydantic ValidationError"
    - "Graceful fallback: generate_layout_image and parse_layout_image return None on failure"
    - "merge_content_into_layout maps EditorialContent fields to block types via isinstance"

key-files:
  created:
    - src/editorial_ai/services/editorial_service.py
    - src/editorial_ai/prompts/editorial.py
    - tests/test_editorial_service.py
  modified:
    - src/editorial_ai/config.py

key-decisions:
  - "Reuse curation_service utilities (retry_on_api_error, _strip_markdown_fences, get_genai_client) via import"
  - "response_modalities=['IMAGE', 'TEXT'] for Nano Banana to handle mixed responses"
  - "Vision parse returns list[dict] not typed model to keep flexibility for block structure"
  - "deepcopy in merge_content_into_layout to avoid mutating input layout"

patterns-established:
  - "Editorial pipeline pattern: content gen -> optional image gen -> merge into layout"
  - "Fallback chain: Nano Banana failure -> default template; Vision failure -> default template"

duration: 4min
completed: 2026-02-25
---

# Phase 4 Plan 02: EditorialService Pipeline Summary

**3-step editorial pipeline with Gemini structured output, Nano Banana layout image, Vision AI parsing, output repair loop, and template fallback**

## Performance

- **Duration:** 4 min
- **Started:** 2026-02-25T09:51:00Z
- **Completed:** 2026-02-25T09:54:42Z
- **Tasks:** 3
- **Files modified:** 4

## Accomplishments
- EditorialService implementing full 3-step pipeline: content gen -> layout image -> vision parse -> merge
- 4 prompt templates for content generation, layout image, layout parsing, and output repair
- Output repair loop with configurable max attempts for Pydantic validation failures
- 10 unit tests covering success paths, repair loop, and all fallback scenarios (63 total tests pass)

## Task Commits

Each task was committed atomically:

1. **Task 1: Editorial prompts and config extension** - `9f37a5c` (feat)
2. **Task 2: EditorialService implementation** - `cd1a5a4` (feat)
3. **Task 3: EditorialService unit tests** - `dd1a2f8` (test)

## Files Created/Modified
- `src/editorial_ai/prompts/editorial.py` - 4 prompt builders for editorial pipeline
- `src/editorial_ai/services/editorial_service.py` - EditorialService with 7 methods and full pipeline
- `src/editorial_ai/config.py` - Added editorial_model, nano_banana_model, editorial_max_repair_attempts
- `tests/test_editorial_service.py` - 10 unit tests with mocked Gemini API

## Decisions Made
- Reuse curation_service utilities via import rather than duplicating code
- response_modalities=['IMAGE', 'TEXT'] for Nano Banana to handle mixed text+image responses
- Vision parse returns untyped list[dict] for flexibility in block structure interpretation
- deepcopy in merge to ensure immutability of input layout

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- EditorialService.create_editorial() is ready to be called from LangGraph editorial node (04-03)
- All Gemini interactions are mocked in tests; live testing requires GOOGLE_API_KEY
- Template fallback ensures the pipeline never fails completely
- Prompt templates may need iterative refinement based on actual Gemini output quality

---
*Phase: 04-editorial-agent-generation-layout*
*Completed: 2026-02-25*
