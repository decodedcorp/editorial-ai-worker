---
phase: quick-001
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - src/editorial_ai/prompts/editorial.py
  - src/editorial_ai/models/layout.py
  - src/editorial_ai/services/editorial_service.py
  - admin/package.json
  - admin/src/components/block-renderer.tsx
autonomous: true

must_haves:
  truths:
    - "AI generates layouts using pull_quote, product_showcase, celeb_feature, divider blocks - not just hero+headline+body+gallery repeats"
    - "Default fallback template includes pull_quote and second body_text section for richer layouts"
    - "Empty blocks (image_gallery with no images, body_text with empty paragraphs) are filtered out after merge"
    - "Each block animates in with a scroll-triggered fade-in/slide-up on the magazine preview page"
  artifacts:
    - path: "src/editorial_ai/prompts/editorial.py"
      provides: "Improved layout prompts with diversity instructions and examples"
    - path: "src/editorial_ai/models/layout.py"
      provides: "Richer default template with pull_quote, second body_text, image_gallery"
    - path: "src/editorial_ai/services/editorial_service.py"
      provides: "Empty block filtering in merge_content_into_layout"
    - path: "admin/src/components/block-renderer.tsx"
      provides: "GSAP scroll-triggered animations on each block"
  key_links:
    - from: "src/editorial_ai/services/editorial_service.py"
      to: "merge_content_into_layout"
      via: "post-merge filter removing empty blocks"
      pattern: "_is_block_empty"
---

<objective>
Improve editorial layout diversity and add scroll animations.

Purpose: The AI pipeline currently generates monotonous layouts (hero+headline+body+gallery repeats with empty blocks). This plan fixes the prompt to encourage diverse block usage, enriches the fallback template, filters empty blocks post-merge, and adds GSAP scroll animations to the frontend renderer.

Output: Updated prompts, richer default template, empty block filtering, animated block rendering.
</objective>

<execution_context>
@/Users/kiyeol/.claude-pers/get-shit-done/workflows/execute-plan.md
@/Users/kiyeol/.claude-pers/get-shit-done/templates/summary.md
</execution_context>

<context>
@src/editorial_ai/prompts/editorial.py
@src/editorial_ai/models/layout.py
@src/editorial_ai/services/editorial_service.py
@admin/src/components/block-renderer.tsx
</context>

<tasks>

<task type="auto">
  <name>Task 1: Improve AI layout prompts and enrich default template</name>
  <files>
    src/editorial_ai/prompts/editorial.py
    src/editorial_ai/models/layout.py
  </files>
  <action>
**In `src/editorial_ai/prompts/editorial.py`:**

1. Update `build_layout_image_prompt()` to explicitly request diverse block types:
   - Change the "Include these section areas" list to enumerate ALL block types: hero, headline, body_text (x2), pull_quote, image_gallery, product_showcase, celeb_feature, divider(s), hashtag_bar, credits
   - Add instruction: "Vary the layout - do NOT repeat the same block type consecutively. Use pull quotes between text sections. Add dividers to create visual rhythm."
   - Add 2-3 example layout patterns, e.g.:
     Pattern A: hero -> headline -> body_text -> pull_quote -> image_gallery -> body_text -> divider -> product_showcase -> celeb_feature -> hashtag_bar -> credits
     Pattern B: hero -> headline -> body_text -> divider -> celeb_feature -> pull_quote -> body_text -> image_gallery -> product_showcase -> hashtag_bar -> credits

2. Update `build_layout_parsing_prompt()` to guide the parser toward diversity:
   - After the rules section, add: "중요: 다양한 블록 타입을 사용하세요. body_text나 image_gallery만 반복하지 마세요. pull_quote, product_showcase, celeb_feature, divider 블록을 반드시 포함하세요."
   - Add rule: "- pull_quote, product_showcase, celeb_feature 블록을 각각 최소 1개씩 포함하세요"

**In `src/editorial_ai/models/layout.py`:**

3. Update `create_default_template()` to produce a richer fallback:
   - New block sequence: HeroBlock -> HeadlineBlock -> BodyTextBlock(paragraphs=[]) -> PullQuoteBlock(quote="") -> DividerBlock(style="line") -> ImageGalleryBlock(images=[], layout_style="grid") -> BodyTextBlock(paragraphs=[]) -> DividerBlock(style="space") -> ProductShowcaseBlock(products=[]) -> CelebFeatureBlock(celebs=[]) -> DividerBlock(style="line") -> HashtagBarBlock(hashtags=[keyword]) -> CreditsBlock(entries=[CreditEntry(role="AI Editor", name="decoded editorial")])
   - Import ImageGalleryBlock at the top of the function or use the existing import
  </action>
  <verify>
    Run: `cd /Users/kiyeol/development/decoded/editorial-ai-worker && python -c "from editorial_ai.models.layout import create_default_template; t = create_default_template('test', 'Test Title'); print([b.type for b in t.blocks])"` and confirm output includes pull_quote, image_gallery, two body_text blocks, multiple dividers.
    Run: `python -c "from editorial_ai.prompts.editorial import build_layout_parsing_prompt; p = build_layout_parsing_prompt('test', ['hero','headline']); print('pull_quote' in p)"` and confirm True.
  </verify>
  <done>
    - build_layout_image_prompt includes diverse block examples and anti-repetition instructions
    - build_layout_parsing_prompt mandates pull_quote, product_showcase, celeb_feature inclusion
    - create_default_template returns 13 blocks including pull_quote, image_gallery, two body_text, three dividers
  </done>
</task>

<task type="auto">
  <name>Task 2: Filter empty blocks after merge</name>
  <files>
    src/editorial_ai/services/editorial_service.py
  </files>
  <action>
Add an `_is_block_empty` static/private method to `EditorialService` that checks if a block has no meaningful content:

```python
@staticmethod
def _is_block_empty(block) -> bool:
    """Check if a block has no meaningful content and should be filtered."""
    if isinstance(block, BodyTextBlock):
        return not block.paragraphs or all(not p.strip() for p in block.paragraphs)
    if isinstance(block, ImageGalleryBlock):
        return not block.images
    if isinstance(block, PullQuoteBlock):
        return not block.quote or not block.quote.strip()
    if isinstance(block, ProductShowcaseBlock):
        return not block.products
    if isinstance(block, CelebFeatureBlock):
        return not block.celebs
    if isinstance(block, HashtagBarBlock):
        return not block.hashtags
    if isinstance(block, CreditsBlock):
        return not block.entries
    if isinstance(block, HeadlineBlock):
        return not block.text or not block.text.strip()
    if isinstance(block, HeroBlock):
        return not block.image_url and not block.overlay_title
    # DividerBlock is never empty (it's structural)
    return False
```

Import `ImageGalleryBlock` at the top of the file (it's not currently imported).

At the end of `merge_content_into_layout()`, before the return, add filtering:

```python
# Filter out blocks with no meaningful content
new_layout.blocks = [b for b in new_layout.blocks if not self._is_block_empty(b)]
```

This ensures empty image_gallery blocks (the main offender from the problem description) and any other empty blocks are removed from the final output.
  </action>
  <verify>
    Run: `cd /Users/kiyeol/development/decoded/editorial-ai-worker && python -c "
from editorial_ai.models.layout import ImageGalleryBlock, BodyTextBlock, DividerBlock, HeroBlock, HeadlineBlock
from editorial_ai.services.editorial_service import EditorialService
svc = EditorialService.__new__(EditorialService)
assert svc._is_block_empty(ImageGalleryBlock(images=[])) == True
assert svc._is_block_empty(BodyTextBlock(paragraphs=[])) == True
assert svc._is_block_empty(BodyTextBlock(paragraphs=['hello'])) == False
assert svc._is_block_empty(DividerBlock()) == False
assert svc._is_block_empty(HeroBlock(image_url='', overlay_title='Test')) == False
print('All assertions passed')
"`
  </verify>
  <done>
    - _is_block_empty correctly identifies empty blocks for all block types
    - merge_content_into_layout filters out empty blocks before returning
    - DividerBlocks are preserved (structural, never considered empty)
  </done>
</task>

<task type="auto">
  <name>Task 3: Add GSAP scroll animations to BlockRenderer</name>
  <files>
    admin/package.json
    admin/src/components/block-renderer.tsx
  </files>
  <action>
1. Install gsap in the admin directory:
   `cd /Users/kiyeol/development/decoded/editorial-ai-worker/admin && npm install gsap`

2. Update `admin/src/components/block-renderer.tsx`:
   - Import gsap and ScrollTrigger: `import gsap from "gsap"; import { ScrollTrigger } from "gsap/ScrollTrigger";`
   - Register the plugin: `gsap.registerPlugin(ScrollTrigger);`
   - Create a wrapper component `AnimatedBlock` that wraps each block with a ref and useEffect for scroll animation:

```tsx
import { useRef, useEffect } from "react";

function AnimatedBlock({ children, index }: { children: React.ReactNode; index: number }) {
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!ref.current) return;

    gsap.fromTo(
      ref.current,
      { opacity: 0, y: 40 },
      {
        opacity: 1,
        y: 0,
        duration: 0.7,
        ease: "power2.out",
        delay: index * 0.05,
        scrollTrigger: {
          trigger: ref.current,
          start: "top 85%",
          toggleActions: "play none none none",
        },
      }
    );

    return () => {
      ScrollTrigger.getAll().forEach((t) => {
        if (t.trigger === ref.current) t.kill();
      });
    };
  }, [index]);

  return <div ref={ref}>{children}</div>;
}
```

3. Wrap each block in the render loop with `AnimatedBlock`:
   ```tsx
   <BlockErrorBoundary key={i} blockType={type!} blockData={block}>
     <AnimatedBlock index={i}>
       <Component block={block} designSpec={designSpec ?? undefined} />
     </AnimatedBlock>
   </BlockErrorBoundary>
   ```

Do NOT animate the "Unknown block type" fallback div - only wrap the Component render path.
  </action>
  <verify>
    Run: `cd /Users/kiyeol/development/decoded/editorial-ai-worker/admin && npm run build` and confirm build succeeds with no errors.
    Verify gsap is in package.json dependencies: `grep gsap package.json`
  </verify>
  <done>
    - gsap installed as dependency in admin/package.json
    - Each block in BlockRenderer has a scroll-triggered fade-in/slide-up animation
    - Animations are staggered by block index (0.05s delay per block)
    - ScrollTrigger instances are cleaned up on unmount
    - Build passes successfully
  </done>
</task>

</tasks>

<verification>
1. Python prompt functions include diversity instructions: `python -c "from editorial_ai.prompts.editorial import build_layout_image_prompt; print(build_layout_image_prompt('test', 'Test', 8))" | grep -c "pull_quote"` returns >= 1
2. Default template is richer: `python -c "from editorial_ai.models.layout import create_default_template; t = create_default_template('k', 't'); print(len(t.blocks))"` returns 13
3. Empty block filtering works: verify via the Task 2 assertions
4. Admin builds: `cd admin && npm run build` passes
5. GSAP installed: `grep gsap admin/package.json` shows version
</verification>

<success_criteria>
- AI layout prompts explicitly instruct diverse block type usage with examples
- Default template includes 13 blocks covering all block types
- Empty blocks are filtered out after content merge
- BlockRenderer animates each block with GSAP scroll-triggered fade-in/slide-up
- Both Python and Next.js codebases pass their respective checks (import validation, build)
</success_criteria>

<output>
After completion, create `.planning/quick/001-enhance-layout-diversity-and-animations/001-SUMMARY.md`
</output>
