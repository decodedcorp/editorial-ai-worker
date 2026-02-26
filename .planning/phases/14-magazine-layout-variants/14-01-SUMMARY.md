---
phase: 14-magazine-layout-variants
plan: 01
subsystem: layout-models
tags: [pydantic, typescript, layout-variant, block-renderer, backward-compat]
dependency_graph:
  requires: [quick-001]
  provides: [layout_variant field on all block models, per-block width control in BlockRenderer]
  affects: [14-02, 14-03, 14-04]
tech_stack:
  added: []
  patterns: [per-block width wrapper, variant-based layout branching]
key_files:
  created: []
  modified:
    - src/editorial_ai/models/layout.py
    - admin/src/lib/types.ts
    - admin/src/components/block-renderer.tsx
decisions:
  - id: layout-variant-literal-types
    description: "Used Literal types for layout_variant (not Enum) to match existing AnimationType pattern"
  - id: width-class-categories
    description: "Four width categories: full-bleed (w-full), wide (max-w-5xl), default (max-w-3xl), narrow (max-w-xl)"
  - id: image-gallery-dual-fields
    description: "ImageGalleryBlock keeps layout_style for backward compat; layout_variant adds new variants"
metrics:
  duration: "2m 23s"
  completed: 2026-02-26
---

# Phase 14 Plan 01: Layout Variant Schema Foundation Summary

**One-liner:** layout_variant Literal fields on all 10 Python/TS block models with per-block width wrapper in BlockRenderer

## What Was Done

### Task 1: Add layout_variant to all Python block models
- Added 10 Literal variant types: HeroVariant, HeadlineVariant, BodyTextVariant, ImageGalleryVariant, PullQuoteVariant, ProductShowcaseVariant, CelebFeatureVariant, DividerVariant, HashtagBarVariant, CreditsVariant
- Added `layout_variant: Optional[XxxVariant] = None` to all 10 block models
- ImageGalleryBlock retains existing `layout_style` field; `layout_variant` extends with new options
- Commit: `21167b9`

### Task 2: Add layout_variant to TypeScript types and restructure BlockRenderer
- Added matching `layout_variant` union types to all 10 TS block interfaces
- Changed `<article>` from `mx-auto max-w-3xl` to `w-full`
- Added `getBlockWidthClass()` helper with variant-to-width mapping
- Four width categories: full-bleed (`w-full`), wide (`max-w-5xl mx-auto`), default (`max-w-3xl mx-auto`), narrow (`max-w-xl mx-auto`)
- Unknown block type fallback also gets `max-w-3xl mx-auto`
- Commit: `4e86bbd`

## Verification Results

1. Python import: `from editorial_ai.models.layout import *` -- OK
2. Python HeroBlock: `layout_variant=None` (default), `layout_variant='full_bleed'` -- both valid
3. TypeScript: `npx tsc --noEmit` -- zero errors
4. Backward compat: blocks without layout_variant get `max-w-3xl mx-auto` (identical to previous `mx-auto max-w-3xl`)

## Deviations from Plan

None -- plan executed exactly as written.

## Decisions Made

| ID | Decision | Rationale |
|----|----------|-----------|
| layout-variant-literal-types | Used Literal types, not Enum | Matches existing AnimationType pattern; JSON-serializable without custom encoder |
| width-class-categories | 4 width tiers | Covers full-bleed immersive, wide editorial, standard reading, and narrow focus layouts |
| image-gallery-dual-fields | Keep layout_style alongside layout_variant | Backward compatibility -- existing content uses layout_style for grid/carousel/masonry |

## Next Phase Readiness

- All block models now have `layout_variant` field ready for component-level rendering
- Plans 14-02 through 14-04 can branch on `layout_variant` in individual block components
- No blockers identified
