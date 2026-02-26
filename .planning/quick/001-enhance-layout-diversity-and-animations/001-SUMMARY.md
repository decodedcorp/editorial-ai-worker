---
phase: quick-001
plan: 01
subsystem: editorial-pipeline + admin-renderer
tags: [layout, gsap, animation, prompts, block-diversity]
dependency-graph:
  requires: [v1.1-complete]
  provides: [diverse-layouts, per-block-animations, empty-block-filtering]
  affects: [magazine-renderer, editorial-pipeline]
tech-stack:
  added: [gsap@3.14.2]
  patterns: [animation-presets, scroll-trigger, empty-block-filter]
key-files:
  created: []
  modified:
    - src/editorial_ai/models/layout.py
    - src/editorial_ai/prompts/editorial.py
    - src/editorial_ai/services/editorial_service.py
    - admin/src/lib/types.ts
    - admin/src/components/block-renderer.tsx
    - admin/package.json
    - admin/pnpm-lock.yaml
metrics:
  duration: 4m
  completed: 2026-02-26
---

# Quick Task 001: Enhance Layout Diversity and Animations Summary

Diverse block prompts with AI-decided per-block GSAP animations and empty block post-merge filtering.

## What Was Done

### Task 1: Improve AI Layout Prompts, Enrich Default Template, Add Animation Field

**Commit:** ab947fe

- **layout.py:** Added `AnimationType` literal type and `animation` field to all 10 block models (HeroBlock, HeadlineBlock, BodyTextBlock, ImageGalleryBlock, PullQuoteBlock, ProductShowcaseBlock, CelebFeatureBlock, DividerBlock, HashtagBarBlock, CreditsBlock)
- **layout.py:** Enriched `create_default_template()` from 8 to 13 blocks, now includes PullQuoteBlock, ImageGalleryBlock, 2x BodyTextBlock, 3x DividerBlock, with sensible animation defaults per block type
- **editorial.py / build_layout_image_prompt():** Added all 10 block types to section list, anti-repetition instruction, and 2 example layout patterns (Pattern A/B)
- **editorial.py / build_layout_parsing_prompt():** Added animation field to output format, animation guide per block type, diversity mandate requiring pull_quote/product_showcase/celeb_feature inclusion

### Task 2: Filter Empty Blocks After Merge

**Commit:** ab947fe (same commit as Task 1 - backend atomic)

- **editorial_service.py:** Added `_is_block_empty()` static method checking all block types for meaningful content
- **editorial_service.py:** Added ImageGalleryBlock to imports
- **editorial_service.py:** Post-merge filter removes empty blocks (DividerBlock preserved as structural)

### Task 3: Add GSAP Scroll Animations with AI-Decided Presets

**Commit:** aa3316b

- **types.ts:** Added `AnimationType` union type and `animation` field to all 10 block interfaces
- **package.json:** Installed gsap@3.14.2
- **block-renderer.tsx:** Created `AnimatedBlock` wrapper with 6 animation presets:
  - `fade-up`: opacity 0 + y:40 -> visible
  - `fade-in`: opacity 0 -> visible
  - `slide-left`: opacity 0 + x:-60 -> visible
  - `slide-right`: opacity 0 + x:60 -> visible
  - `scale-in`: opacity 0 + scale:0.9 -> visible
  - `parallax`: opacity 0 + y:60 -> visible (1.2s duration)
- Animation reads from `block.animation` field (AI-decided), defaults to `fade-up`
- ScrollTrigger fires at `top 85%` with staggered delay per block index
- Cleanup on unmount

### Additional Requirement: AI-Decided Per-Block Animation

**Commit:** ab947fe + aa3316b (integrated into both backend and frontend commits)

- AI now decides which GSAP animation each block gets via the `animation` field in layout parsing
- Prompt includes animation guide mapping block types to recommended animations
- `_build_layout_from_parsed()` passes animation from parsed blocks to block constructors
- Frontend reads and applies the AI-decided animation per block

## Deviations from Plan

None - plan executed exactly as written, with additional requirement integrated into the planned tasks.

## Verification Results

1. Default template produces 13 blocks: `['hero', 'headline', 'body_text', 'pull_quote', 'divider', 'image_gallery', 'body_text', 'divider', 'product_showcase', 'celeb_feature', 'divider', 'hashtag_bar', 'credits']`
2. Parsing prompt includes `pull_quote` and `animation` references
3. Empty block filtering: all assertions passed (ImageGalleryBlock(images=[]) -> empty, BodyTextBlock(paragraphs=[]) -> empty, DividerBlock() -> not empty)
4. Animation defaults verified: hero=parallax, headline=fade-up, pull_quote=scale-in, product_showcase=slide-right, etc.
5. Admin build: passes successfully with gsap@3.14.2

## Decisions Made

| Decision | Rationale |
|----------|-----------|
| Animation field is Optional[...] = None | Backward compatible with existing data; frontend defaults to fade-up |
| 6 animation presets (not more) | Covers all common entrance effects without bloat |
| DividerBlock never considered empty | Structural element providing visual rhythm |
| Animation integrated into parsing prompt, not separate step | Single AI call decides both layout structure and animation |
