---
phase: 13-pipeline-advanced
plan: 02
subsystem: api
tags: [rubric, classifier, content-type, review, adaptive-evaluation]

requires:
  - phase: 05-review-loop
    provides: ReviewService hybrid evaluation pipeline
  - phase: 10-observability-backend
    provides: record_token_usage instrumentation
provides:
  - ContentType enum with fashion_magazine, tech_blog, lifestyle, default
  - Keyword-based content type classifier
  - RubricConfig with weighted criteria per content type
  - Adaptive review prompt generation from rubric config
affects: [13-03-pipeline-advanced]

tech-stack:
  added: []
  patterns:
    - "Adaptive rubric pattern: classify -> lookup -> inject into prompt"
    - "Longest-match-first keyword classification for multi-domain disambiguation"

key-files:
  created:
    - src/editorial_ai/rubrics/__init__.py
    - src/editorial_ai/rubrics/registry.py
    - src/editorial_ai/rubrics/classifier.py
    - tests/test_rubrics.py
  modified:
    - src/editorial_ai/prompts/review.py
    - src/editorial_ai/services/review_service.py
    - src/editorial_ai/nodes/review.py

key-decisions:
  - "Longest-match-first keyword sorting to prevent 'trend' stealing 'home decor trends' from lifestyle"
  - "DEFAULT rubric = FASHION_MAGAZINE (fashion-first pipeline)"
  - "Backward compatible: rubric_config=None produces original 3-criteria prompt"
  - "TYPE_CHECKING guard for RubricConfig import to avoid circular imports"

patterns-established:
  - "Adaptive rubric: classify_content_type -> get_rubric -> build_review_prompt(rubric_config=...)"
  - "Registry pattern: RUBRIC_REGISTRY dict keyed by ContentType enum"

duration: 9min
completed: 2026-02-26
---

# Phase 13 Plan 02: Adaptive Rubrics Summary

**Keyword-based content type classifier with per-type weighted review criteria injected into LLM-as-a-Judge prompt**

## Performance

- **Duration:** 9 min
- **Started:** 2026-02-26T09:31:40Z
- **Completed:** 2026-02-26T09:40:24Z
- **Tasks:** 2
- **Files modified:** 7

## Accomplishments
- ContentType enum (fashion_magazine, tech_blog, lifestyle, default) with keyword-domain classifier
- RubricConfig with weighted criteria per content type (e.g., tech has 1.2x fact_accuracy weight)
- Dynamic review prompt generation that adapts evaluation criteria to content type
- Full backward compatibility -- existing code paths unchanged when rubric_config is None

## Task Commits

Each task was committed atomically:

1. **Task 1: Rubric registry + content classifier** - `dca5ee6` (feat)
2. **Task 2: Integrate rubrics into review prompt + service + node** - `f269031` (feat)

## Files Created/Modified
- `src/editorial_ai/rubrics/__init__.py` - Package exports
- `src/editorial_ai/rubrics/registry.py` - ContentType enum, RubricConfig, RUBRIC_REGISTRY, get_rubric
- `src/editorial_ai/rubrics/classifier.py` - classify_content_type with keyword-domain matching
- `src/editorial_ai/prompts/review.py` - build_review_prompt with optional rubric_config parameter
- `src/editorial_ai/services/review_service.py` - evaluate/evaluate_with_llm accept rubric_config
- `src/editorial_ai/nodes/review.py` - Classifies content type and passes rubric to service
- `tests/test_rubrics.py` - 16 tests for classifier, registry, and prompt integration

## Decisions Made
- Longest-match-first keyword sorting prevents ambiguous matches (e.g., "home decor trends" correctly classified as lifestyle, not fashion due to "trend" substring)
- DEFAULT rubric mirrors FASHION_MAGAZINE since this is a fashion-first pipeline
- TYPE_CHECKING guard for RubricConfig import avoids circular import between rubrics and prompts
- Additive changes only to review_service.py and review.py to avoid merge conflicts with parallel plan 13-01

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed keyword classifier matching ambiguity**
- **Found during:** Task 2 (test verification)
- **Issue:** "home decor trends" matched "trend" (fashion) before "home decor" (lifestyle) due to dict iteration order
- **Fix:** Sort keyword matches by length descending (_SORTED_KEYWORDS) so longer/more specific matches win
- **Files modified:** src/editorial_ai/rubrics/classifier.py
- **Verification:** test_classify_lifestyle_keyword passes
- **Committed in:** f269031 (Task 2 commit)

---

**Total deviations:** 1 auto-fixed (1 bug)
**Impact on plan:** Essential fix for correct classification behavior. No scope creep.

## Issues Encountered
- Plan 13-01 (model router) modified review_service.py concurrently, adding routing_reason and revision_count params. Changes merged cleanly since both plans used additive-only modifications.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Adaptive rubric system ready for use in production review pipeline
- Plan 13-03 can build on content type classification for further pipeline intelligence

---
*Phase: 13-pipeline-advanced*
*Completed: 2026-02-26*
