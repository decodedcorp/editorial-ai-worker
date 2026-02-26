---
phase: 11-magazine-renderer-enhancement
plan: 01
subsystem: ai-pipeline
tags: [pydantic, gemini, design-spec, langgraph, google-fonts, theming]

# Dependency graph
requires:
  - phase: 03-editorial-generation
    provides: "EditorialService, MagazineLayout model, editorial_node"
  - phase: 02-curation-pipeline
    provides: "CurationService, curation_node, get_genai_client pattern"
provides:
  - "DesignSpec Pydantic model (FontPairing, ColorPalette, layout density, mood)"
  - "design_spec_node in LangGraph pipeline between curation and source"
  - "DesignSpecService with Gemini structured output and fallback"
  - "MagazineLayout.design_spec field for frontend consumption"
affects:
  - 11-02 (renderer component upgrade will consume design_spec)
  - 11-03 (CSS variable generation from design_spec)
  - 11-04 (font loading from design_spec.font_pairing)

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Gemini response_schema for structured DesignSpec output"
    - "Fallback-to-default pattern for non-critical pipeline nodes"

key-files:
  created:
    - "src/editorial_ai/models/design_spec.py"
    - "src/editorial_ai/prompts/design_spec.py"
    - "src/editorial_ai/services/design_spec_service.py"
    - "src/editorial_ai/nodes/design_spec.py"
  modified:
    - "src/editorial_ai/state.py"
    - "src/editorial_ai/graph.py"
    - "src/editorial_ai/models/layout.py"
    - "src/editorial_ai/nodes/editorial.py"
    - "src/editorial_ai/nodes/stubs.py"
    - "src/editorial_ai/models/__init__.py"

key-decisions:
  - "DesignSpec uses Gemini response_schema for reliable JSON, not free-text parsing"
  - "design_spec_node failure returns default spec (never crashes pipeline)"
  - "design_spec injected into MagazineLayout so it persists in layout_json to DB and frontend"

patterns-established:
  - "Fallback node pattern: try AI generation, catch-all returns sensible default"
  - "Design spec travels state -> editorial_node -> MagazineLayout -> DB -> frontend"

# Metrics
duration: 3min
completed: 2026-02-26
---

# Phase 11 Plan 01: DesignSpec Pipeline Node Summary

**AI-driven design spec generation via Gemini with FontPairing, ColorPalette, mood, and layout density — wired into LangGraph between curation and source with safe fallback**

## Performance

- **Duration:** 3 min
- **Started:** 2026-02-26T05:23:09Z
- **Completed:** 2026-02-26T05:26:10Z
- **Tasks:** 2
- **Files modified:** 10

## Accomplishments

- DesignSpec Pydantic model captures font pairing (curated Google Fonts), color palette, layout density, mood, hero aspect ratio, and drop cap
- design_spec_node generates dynamic per-keyword themes via Gemini structured output
- Pipeline topology updated: curation -> design_spec -> source -> editorial -> enrich -> review -> admin_gate -> publish
- editorial_node injects design_spec into MagazineLayout for end-to-end delivery to frontend

## Task Commits

Each task was committed atomically:

1. **Task 1: DesignSpec Pydantic model + prompt** - `158a95c` (feat)
2. **Task 2: DesignSpec service + node + graph wiring + layout model** - `4dffd7e` (feat)

## Files Created/Modified

- `src/editorial_ai/models/design_spec.py` - FontPairing, ColorPalette, DesignSpec models + default factory
- `src/editorial_ai/prompts/design_spec.py` - Prompt builder for Gemini design spec generation
- `src/editorial_ai/services/design_spec_service.py` - DesignSpecService with Gemini structured output
- `src/editorial_ai/nodes/design_spec.py` - LangGraph node wrapping the service
- `src/editorial_ai/state.py` - Added design_spec field to EditorialPipelineState
- `src/editorial_ai/graph.py` - Inserted design_spec node between curation and source
- `src/editorial_ai/models/layout.py` - Added design_spec field to MagazineLayout
- `src/editorial_ai/nodes/editorial.py` - Injects design_spec from state into layout
- `src/editorial_ai/nodes/stubs.py` - Added stub_design_spec for testing
- `src/editorial_ai/models/__init__.py` - Exported new design_spec models

## Decisions Made

- Used Gemini `response_schema=DesignSpec` for structured JSON output instead of free-text parsing — more reliable than regex/markdown fence stripping
- design_spec_node catches all exceptions and returns default_design_spec() — design spec is a non-critical enhancement, must never block the pipeline
- DesignSpec injected into MagazineLayout at editorial_node level so it persists in layout_json through DB to frontend — avoids needing a separate API endpoint

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- DesignSpec is generated and stored in layout_json — ready for 11-02 (renderer component upgrade)
- Frontend can read `layout_json.design_spec` for font pairing, color palette, layout density, mood
- stub_design_spec available for testing downstream plans

---
*Phase: 11-magazine-renderer-enhancement*
*Completed: 2026-02-26*
