---
phase: 06-review-agent-feedback-loop
plan: 02
subsystem: ai-pipeline
tags: [feedback-injection, prompt-engineering, editorial, retry-loop, langgraph]

# Dependency graph
requires:
  - phase: 06-review-agent-feedback-loop
    provides: ReviewResult model with criteria and suggestions for feedback injection
  - phase: 04-editorial-agent-generation
    provides: EditorialService, editorial_node, editorial prompts
provides:
  - build_content_generation_prompt_with_feedback() for feedback-aware regeneration
  - EditorialService.create_editorial() with optional feedback_history and previous_draft
  - Editorial node reads feedback_history from state and passes to service on retry
affects: [06-03 retry loop wiring, 07-admin-backend]

# Tech tracking
tech-stack:
  added: []
  patterns: [feedback-prepend pattern (feedback BEFORE main prompt for LLM attention priority)]

key-files:
  created: []
  modified:
    - src/editorial_ai/prompts/editorial.py
    - src/editorial_ai/services/editorial_service.py
    - src/editorial_ai/nodes/editorial.py
    - tests/test_editorial_node.py

key-decisions:
  - "Feedback prepended BEFORE main prompt for maximum LLM attention"
  - "Only failed criteria included in feedback (passed criteria are noise)"
  - "Previous draft summarized by title only (not full content) to avoid reproducing same mistakes"
  - "Explicit instruction to write completely new draft prevents copy-paste from failed version"

patterns-established:
  - "Feedback-prepend pattern: review failures placed before generation instructions for LLM prioritization"
  - "Optional keyword-only params for backward-compatible API extension (feedback_history, previous_draft)"

# Metrics
duration: 2min
completed: 2026-02-25
---

# Phase 6 Plan 2: Editorial Feedback Injection Summary

**Feedback-aware prompt builder prepends review failures before editorial generation instructions, with editorial node reading feedback_history from state on retry iterations**

## Performance

- **Duration:** ~2 min
- **Started:** 2026-02-25T11:20:27Z
- **Completed:** 2026-02-25T11:22:30Z
- **Tasks:** 2
- **Files modified:** 4

## Accomplishments
- Feedback-aware prompt builder that prepends failed review criteria before main editorial instructions
- EditorialService extended with optional feedback_history and previous_draft parameters (backward-compatible)
- Editorial node reads feedback_history from state and passes it to service on retry
- 2 new tests verifying feedback passthrough and first-run no-feedback behavior

## Task Commits

Each task was committed atomically:

1. **Task 1: Add feedback-aware prompt builder and update EditorialService** - `341350a` (feat)
2. **Task 2: Update editorial node to inject feedback on retry** - `7af192c` (feat)

## Files Created/Modified
- `src/editorial_ai/prompts/editorial.py` - Added build_content_generation_prompt_with_feedback() function
- `src/editorial_ai/services/editorial_service.py` - Extended generate_content and create_editorial with optional feedback params
- `src/editorial_ai/nodes/editorial.py` - Reads feedback_history and current_draft from state, passes to service
- `tests/test_editorial_node.py` - 2 new tests for feedback injection and no-feedback first-run

## Decisions Made
- Feedback section prepended BEFORE main prompt (LLMs pay more attention to early context)
- Only failed criteria included in feedback to reduce noise
- Previous draft summarized by title only to avoid reproducing same failed content
- Explicit Korean instruction "완전히 새로운 초안을 작성하세요" prevents copy-paste behavior
- Keyword-only optional params ensure no existing callers break

## Deviations from Plan
None - plan executed exactly as written.

## Issues Encountered
None

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Feedback injection complete, ready for retry loop wiring in 06-03
- All 103 existing tests pass -- no regressions
- Editorial node now reads feedback_history from state, enabling the review->editorial retry cycle

---
*Phase: 06-review-agent-feedback-loop*
*Completed: 2026-02-25*
