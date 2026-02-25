---
phase: 04-editorial-agent-generation-layout
plan: 01
subsystem: models
tags: [pydantic, magazine-layout, block-schema, discriminated-union, gemini-compatible]

requires:
  - phase: 03-curation-agent
    provides: CuratedTopic model pattern, Pydantic v2 conventions
provides:
  - MagazineLayout Pydantic schema with 10 block types (frontend renderer contract)
  - EditorialContent intermediate model for Gemini structured output
  - create_default_template() factory for Nano Banana fallback
  - KeyValuePair pattern for Gemini-compatible metadata
affects: [04-02, 04-03, 05-db-tools, decoded-editorial-frontend]

tech-stack:
  added: []
  patterns:
    - "Discriminated union with Field(discriminator='type') for block types"
    - "KeyValuePair list instead of dict[str, str] for Gemini compatibility"
    - "Separate content model (EditorialContent) from layout model (MagazineLayout)"

key-files:
  created:
    - src/editorial_ai/models/layout.py
    - src/editorial_ai/models/editorial.py
    - tests/test_editorial_models.py
  modified:
    - src/editorial_ai/models/__init__.py

key-decisions:
  - "Block-based schema with 10 types over free-form layout coordinates"
  - "Separate EditorialContent (Gemini output) from MagazineLayout (renderer contract)"
  - "list[KeyValuePair] instead of dict[str, str] for Gemini structured output compatibility"
  - "CreditEntry shared between layout and editorial models"

patterns-established:
  - "Discriminated union: Annotated[LayoutBlock, Field(discriminator='type')]"
  - "Default template factory as fallback pattern"

duration: 2min
completed: 2026-02-25
---

# Phase 4 Plan 01: Magazine Layout Schema & Editorial Models Summary

**Block-based MagazineLayout schema with 10 discriminated block types, EditorialContent intermediate model, and default template factory**

## Performance

- **Duration:** 2 min
- **Started:** 2026-02-25T09:47:09Z
- **Completed:** 2026-02-25T09:49:14Z
- **Tasks:** 2
- **Files modified:** 4

## Accomplishments
- MagazineLayout Pydantic schema with 10 block types using discriminated union
- EditorialContent model for Gemini structured output (content-only, no layout)
- Default template factory for Nano Banana fallback
- 8 unit tests covering roundtrip, discriminator, validation, edge cases

## Task Commits

Each task was committed atomically:

1. **Task 1: Magazine Layout JSON Pydantic schema** - `a4e4495` (feat)
2. **Task 2: Editorial content model and validation tests** - `e45a741` (feat)

## Files Created/Modified
- `src/editorial_ai/models/layout.py` - 10 block types, MagazineLayout container, supporting models, default template factory
- `src/editorial_ai/models/editorial.py` - EditorialContent, ProductMention, CelebMention models
- `src/editorial_ai/models/__init__.py` - Updated exports for all layout and editorial models
- `tests/test_editorial_models.py` - 8 tests covering roundtrip, discriminator, template, validation

## Decisions Made
- Block-based schema with discriminated union over free-form layout — simpler frontend rendering, more reliable Gemini output
- Separate EditorialContent from MagazineLayout — content is what Gemini generates, layout is determined by Nano Banana or template
- list[KeyValuePair] for metadata — avoids Gemini dict[str, str] compatibility issues
- CreditEntry reused from layout.py in editorial.py to avoid duplication

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- MagazineLayout schema is ready for content generation (04-02) and Nano Banana integration (04-03)
- EditorialContent model can be passed directly to Gemini response_schema
- Default template factory provides immediate fallback capability
- Magazine Layout JSON schema contract is now defined for the decoded-editorial frontend team

---
*Phase: 04-editorial-agent-generation-layout*
*Completed: 2026-02-25*
