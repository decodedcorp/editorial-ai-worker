# Phase 11: Magazine Renderer Enhancement - Research

**Researched:** 2026-02-26
**Domain:** Next.js 15 frontend (React 19) magazine renderer + Python/LangGraph backend design_spec node
**Confidence:** HIGH (codebase analysis) / MEDIUM (external patterns)

## Summary

Phase 11 upgrades the existing 10 block components from placeholder rendering to magazine-quality output, adds an AI-driven `design_spec` node to the pipeline, restructures the detail page with tab-based navigation, and adds block-level error resilience.

The codebase is well-structured for this upgrade. The admin app runs Next.js 15.5.12 with React 19, Tailwind CSS v4, shadcn/ui (radix-ui), and already has a `Tabs` component from shadcn. The backend uses Python with LangGraph and Gemini models. All 10 block components currently render placeholders for images (`div` with text like "Hero Image", "Product Photo"). The `BlockRenderer` already handles unknown block types but lacks error boundaries for malformed data within known block types.

Key finding: The project already uses `next/font/google` for Geist fonts, so adding Google Fonts (Georgia, Pretendard, dynamic serif/sans-serif pairings) follows the same established pattern. Image URLs already exist in the data model (`image_url` on HeroBlock, ProductItem, CelebItem, ImageItem) but are completely ignored by the current block components.

**Primary recommendation:** Upgrade block components in-place, add a `DesignSpec` Pydantic model and `design_spec` pipeline node, restructure the detail page to use the existing shadcn `Tabs` component, and wrap each block render in a React error boundary.

## Standard Stack

### Core (Already in project)
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Next.js | 15.5.12 | App framework | Already installed, provides `next/font/google` and `next/image` |
| React | 19.1.0 | UI library | Already installed, class component error boundaries still needed |
| Tailwind CSS | v4 | Styling | Already installed, `@theme` CSS custom properties in globals.css |
| radix-ui (shadcn) | 1.4.3 | UI primitives | Already installed, `Tabs` component already exists |
| Pydantic | (project) | Backend models | Already used for all pipeline models |
| google-genai | (project) | Gemini API | Already used for curation/editorial/enrich services |

### Supporting (Need to add or use)
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `next/image` | built-in | Optimized image loading | All image rendering in blocks (hero, product, celeb, gallery) |
| `next/font/google` | built-in | Google Fonts loading | Loading serif/sans-serif font pairings dynamically |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `next/image` | native `<img>` | `next/image` gives auto optimization, lazy loading, blur placeholder support; requires `remotePatterns` in next.config.ts |
| React error boundary class | react-error-boundary library | Extra dependency; class component approach is 15 lines, no dep needed |
| CSS `filter: blur()` for placeholder | `plaiceholder` library | Library generates real blur hashes server-side; CSS blur on a gradient is simpler and matches the decision for theme-colored fallbacks |

**Installation:**
No new packages needed. All functionality is achievable with existing dependencies.

## Architecture Patterns

### Recommended Project Structure
```
admin/src/
├── components/
│   ├── blocks/                    # EXISTING - upgrade each block component
│   │   ├── hero-block.tsx         # Add real image, dynamic aspect ratio
│   │   ├── product-showcase-block.tsx  # Add product images
│   │   ├── celeb-feature-block.tsx     # Add celeb photos
│   │   ├── image-gallery-block.tsx     # Add gallery images
│   │   ├── body-text-block.tsx         # Add drop cap, magazine typography
│   │   ├── headline-block.tsx          # Add serif fonts
│   │   ├── pull-quote-block.tsx        # Already has Georgia serif
│   │   └── ...                         # Other blocks: minor styling tweaks
│   ├── block-renderer.tsx         # Add ErrorBoundary wrapper
│   ├── block-error-boundary.tsx   # NEW - error boundary component
│   ├── magazine-image.tsx         # NEW - shared image component with blur fallback
│   ├── json-panel.tsx             # Stays as-is, moves into tab
│   └── design-spec-provider.tsx   # NEW - React context for design spec
├── lib/
│   └── types.ts                   # Add DesignSpec interface
└── app/
    └── contents/[id]/
        └── page.tsx               # Restructure to tabs

src/editorial_ai/
├── models/
│   └── design_spec.py            # NEW - DesignSpec Pydantic model
├── nodes/
│   └── design_spec.py            # NEW - design_spec pipeline node
├── services/
│   └── design_spec_service.py    # NEW - Gemini design spec generation
├── prompts/
│   └── design_spec.py            # NEW - design spec prompt
├── state.py                      # Add design_spec field
└── graph.py                      # Insert design_spec node after curation
```

### Pattern 1: Block-Level Error Boundary
**What:** Wrap each block component render in a React error boundary that catches render errors and shows an inline warning instead of crashing the entire page.
**When to use:** Every block render in BlockRenderer.

React 19 still requires class components for error boundaries (no hooks equivalent). The pattern:

```tsx
// block-error-boundary.tsx
"use client";

import { Component, type ErrorInfo, type ReactNode } from "react";

interface Props {
  blockType: string;
  children: ReactNode;
}

interface State {
  hasError: boolean;
  error: Error | null;
}

export class BlockErrorBoundary extends Component<Props, State> {
  constructor(props: Props) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, info: ErrorInfo) {
    console.error(`Block "${this.props.blockType}" render error:`, error, info);
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="rounded border border-amber-300 bg-amber-50 p-4 text-sm text-amber-800">
          <p className="font-medium">{this.props.blockType}: Render error</p>
          <p className="mt-1 text-xs text-amber-600">
            {this.state.error?.message ?? "Unknown error"}
          </p>
          {/* Claude's Discretion: expandable raw JSON here */}
        </div>
      );
    }
    return this.props.children;
  }
}
```

**Usage in BlockRenderer:**
```tsx
{blocks.map((block, i) => {
  const Component = BLOCK_MAP[block.type];
  return (
    <BlockErrorBoundary key={i} blockType={block.type}>
      <Component block={block} />
    </BlockErrorBoundary>
  );
})}
```

### Pattern 2: Magazine Image Component with Progressive Loading
**What:** A shared image component that handles loading states (blur placeholder -> sharp image) and error states (theme gradient fallback).
**When to use:** All image-bearing blocks (hero, product, celeb, gallery).

Two implementation approaches:

**Approach A: `next/image` with blur placeholder (Recommended)**
```tsx
// magazine-image.tsx
"use client";

import Image from "next/image";
import { useState } from "react";

interface MagazineImageProps {
  src: string | null | undefined;
  alt: string;
  className?: string;
  fill?: boolean;
  width?: number;
  height?: number;
  themeColor?: string; // fallback gradient color from design spec
}

export function MagazineImage({ src, alt, className, fill, width, height, themeColor = "#94a3b8" }: MagazineImageProps) {
  const [hasError, setHasError] = useState(false);
  const [isLoading, setIsLoading] = useState(true);

  if (!src || hasError) {
    return (
      <div
        className={cn("flex items-center justify-center", className)}
        style={{
          background: `linear-gradient(135deg, ${themeColor}40, ${themeColor}80)`,
          backdropFilter: "blur(20px)",
        }}
      />
    );
  }

  return (
    <Image
      src={src}
      alt={alt}
      fill={fill}
      width={!fill ? width : undefined}
      height={!fill ? height : undefined}
      className={cn(
        className,
        isLoading && "blur-sm scale-105",
        "transition-all duration-500"
      )}
      onLoad={() => setIsLoading(false)}
      onError={() => setHasError(true)}
      unoptimized // External URLs from Supabase may not be in remotePatterns
    />
  );
}
```

**Important: next/image remotePatterns config required.**
Since images come from Supabase DB (external URLs), `next.config.ts` needs `images.remotePatterns` or use `unoptimized` prop. Given that image URLs come from various sources (DB), using `unoptimized` is safer initially.

### Pattern 3: Design Spec as React Context
**What:** Pass the AI-generated design spec down to all block components via React Context so each block can access font, color, and layout density info.
**When to use:** When rendering blocks with dynamic theming.

```tsx
// design-spec-provider.tsx
"use client";

import { createContext, useContext, type ReactNode } from "react";
import type { DesignSpec } from "@/lib/types";

const DEFAULT_SPEC: DesignSpec = {
  fonts: { headline: "Georgia", body: "Pretendard" },
  colors: { primary: "#1a1a1a", accent: "#6366f1", background: "#ffffff" },
  layout_density: "normal",
  mood: "elegant",
};

const DesignSpecContext = createContext<DesignSpec>(DEFAULT_SPEC);

export function DesignSpecProvider({ spec, children }: { spec?: DesignSpec | null; children: ReactNode }) {
  return (
    <DesignSpecContext.Provider value={spec ?? DEFAULT_SPEC}>
      {children}
    </DesignSpecContext.Provider>
  );
}

export function useDesignSpec() {
  return useContext(DesignSpecContext);
}
```

### Pattern 4: design_spec Pipeline Node (Backend)
**What:** A new node in the LangGraph pipeline that generates a design specification based on curation keywords.
**When to use:** Runs after curation, before editorial.

Graph topology change:
```
BEFORE: curation -> source -> editorial -> enrich -> review
AFTER:  curation -> design_spec -> source -> editorial -> enrich -> review
```

The design_spec node calls Gemini with the curated keywords + category hints to generate:
- Font pairing (headline serif + body sans-serif from Google Fonts)
- Color palette (primary, accent, background, text colors)
- Layout density (compact/normal/spacious)
- Mood/tone (e.g., "minimalist luxury", "vibrant streetwear")
- Hero image aspect ratio (e.g., "16:9", "4:3", "21:9")

### Pattern 5: Tab-Based Detail Page
**What:** Replace vertical stacking (Magazine Preview + collapsible Raw JSON) with tab switching.
**When to use:** The content detail page.

The shadcn `Tabs` component already exists in the project. The restructured page:

```tsx
// Simplified structure
<div>
  <ActionBar />
  <MetadataSection /> {/* title, keyword, dates, review summary */}
  <Tabs defaultValue="magazine">
    <TabsList>
      <TabsTrigger value="magazine">Magazine</TabsTrigger>
      <TabsTrigger value="json">JSON</TabsTrigger>
    </TabsList>
    <TabsContent value="magazine">
      <DesignSpecProvider spec={content.design_spec}>
        <BlockRenderer blocks={content.layout_json.blocks} />
      </DesignSpecProvider>
    </TabsContent>
    <TabsContent value="json">
      <JsonPanel data={content.layout_json} />
    </TabsContent>
  </Tabs>
</div>
```

Note: The detail page is currently a Server Component. Adding tabs requires making the tab container a Client Component. The `Tabs` component from shadcn already has `"use client"`. The `BlockRenderer` itself can stay server, but the `DesignSpecProvider` needs `"use client"`.

### Anti-Patterns to Avoid
- **Rendering all Google Fonts at build time:** Only load the fonts needed by the current design spec. Use `next/font/google` with dynamic subsets.
- **Storing design_spec in Supabase:** Per CONTEXT.md decision, design specs are generated fresh each time. Do NOT persist.
- **Using `<img>` tags directly:** Use `next/image` or a wrapper. Native `<img>` loses optimization, lazy loading, and blur transition.
- **Putting error boundary inside each block component:** Put it OUTSIDE in BlockRenderer. Individual blocks should not know about error handling.
- **Making BlockRenderer a client component:** Keep it server-rendered where possible. Only the image components and interactive parts need `"use client"`.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Image optimization/lazy loading | Custom IntersectionObserver + srcset | `next/image` with `unoptimized` | Handles responsive sizes, lazy loading, format detection |
| Error boundaries | try-catch in render | React class component ErrorBoundary | React lifecycle method is the only supported approach for catching render errors |
| Tab UI | Custom tab state management | shadcn `Tabs` (already in project) | Accessible, keyboard-navigable, styled consistently |
| Font loading | `@import url()` in CSS | `next/font/google` | Automatic font optimization, self-hosting, zero layout shift |
| Blur placeholder animation | JavaScript animation library | CSS `transition` + `blur-sm` Tailwind class | Simple CSS transition is sufficient, no JS overhead |

**Key insight:** The project already has all the UI primitives needed (shadcn Tabs, Tailwind utilities, next/font). The work is upgrading existing components, not building new infrastructure.

## Common Pitfalls

### Pitfall 1: next/image with External URLs
**What goes wrong:** `next/image` throws errors for external image URLs not in `remotePatterns`.
**Why it happens:** Next.js Image optimization proxy requires whitelisted domains.
**How to avoid:** Either (a) add known Supabase storage domains to `remotePatterns` in `next.config.ts`, or (b) use `unoptimized` prop for external URLs. Since image URLs come from arbitrary sources in DB, `unoptimized` is the pragmatic choice.
**Warning signs:** Build errors or runtime 400 responses on images.

### Pitfall 2: Server Component vs Client Component Boundary
**What goes wrong:** Adding `useState` or event handlers to a Server Component causes build failure.
**Why it happens:** The detail page (`page.tsx`) is currently a Server Component. Image loading states and tab switching require client interactivity.
**How to avoid:** Create a client component wrapper for interactive parts (image with loading state, tab container). Keep data fetching in the server component. Pass data down as props.
**Warning signs:** "useState is not a function" or "Event handler cannot be used in Server Component" errors.

### Pitfall 3: Error Boundary Not Catching Async Errors
**What goes wrong:** Error boundaries only catch errors during rendering, not in event handlers or async code.
**Why it happens:** React error boundaries are a lifecycle feature for the render phase only.
**How to avoid:** Error boundaries will catch malformed data that causes render crashes (null property access, type errors). For async image load errors, use `onError` callback on `<Image>` component separately.
**Warning signs:** Unhandled promise rejections bypassing the boundary.

### Pitfall 4: Design Spec Schema Mismatch Between Backend and Frontend
**What goes wrong:** Backend Gemini generates a design_spec JSON that doesn't match the frontend TypeScript interface.
**Why it happens:** LLM output is unpredictable; Pydantic model on backend may pass but frontend expects stricter types.
**How to avoid:** Define a strict Pydantic model with defaults for ALL fields. Frontend DesignSpec type should have fallback defaults for every field. Use optional fields with defaults everywhere.
**Warning signs:** `undefined` values when destructuring design_spec in React components.

### Pitfall 5: Google Fonts Dynamic Loading
**What goes wrong:** Attempting to dynamically load different Google Fonts per design_spec at runtime.
**Why it happens:** `next/font/google` works at build time / module scope, not dynamically per-request.
**How to avoid:** Two strategies:
  - **Strategy A (Recommended):** Pre-load a curated set of 4-6 font families at build time. The design_spec picks from this set. Frontend applies via CSS variable/className.
  - **Strategy B:** Use `@font-face` with Google Fonts CDN URLs in a `<style>` tag at runtime. Loses `next/font` optimization but allows arbitrary fonts.
  Strategy A is better because it keeps fonts optimized and self-hosted while still allowing variety.
**Warning signs:** Layout shift when fonts load, or FOUT (Flash of Unstyled Text).

### Pitfall 6: Hydration Mismatch with Image Loading States
**What goes wrong:** Server-rendered HTML shows "loading" state, client hydration shows "loaded" state (or vice versa).
**Why it happens:** Server doesn't know image load status. Client starts with `isLoading: true` then switches.
**How to avoid:** Start with a CSS-based blur that transitions on `onLoad`. The server render shows the blurred state, client transitions to clear. Both agree on initial state.
**Warning signs:** React hydration warnings in console.

## Code Examples

### Example 1: Upgraded Hero Block with Real Image
```tsx
"use client";

import { useDesignSpec } from "@/components/design-spec-provider";
import { MagazineImage } from "@/components/magazine-image";
import type { HeroBlock } from "@/lib/types";

export function HeroBlockComponent({ block }: { block: HeroBlock }) {
  const spec = useDesignSpec();

  return (
    <div className="relative w-full overflow-hidden rounded-lg"
         style={{ aspectRatio: spec.hero_aspect_ratio ?? "16/9" }}>
      <MagazineImage
        src={block.image_url}
        alt={block.overlay_title ?? "Hero image"}
        fill
        className="object-cover"
        themeColor={spec.colors?.accent}
      />
      {(block.overlay_title || block.overlay_subtitle) && (
        <div className="absolute inset-0 flex flex-col items-center justify-end bg-gradient-to-t from-black/60 to-transparent p-8">
          {block.overlay_title && (
            <h1 className="text-center text-3xl font-bold text-white"
                style={{ fontFamily: `"${spec.fonts?.headline ?? "Georgia"}", serif` }}>
              {block.overlay_title}
            </h1>
          )}
          {block.overlay_subtitle && (
            <p className="mt-2 text-center text-lg text-white/90">
              {block.overlay_subtitle}
            </p>
          )}
        </div>
      )}
    </div>
  );
}
```

### Example 2: Body Text with Drop Cap and Magazine Typography
```tsx
"use client";

import { useDesignSpec } from "@/components/design-spec-provider";
import type { BodyTextBlock } from "@/lib/types";

export function BodyTextBlockComponent({ block }: { block: BodyTextBlock }) {
  const spec = useDesignSpec();
  const paragraphs = block.paragraphs ?? [];

  if (paragraphs.length === 0) return null;

  return (
    <div style={{ fontFamily: `"${spec.fonts?.body ?? "Pretendard"}", sans-serif` }}>
      {paragraphs.map((text, i) => (
        <p
          key={i}
          className={`mb-6 text-[17px] leading-[1.8] text-gray-800 last:mb-0 ${
            i === 0 ? "first-letter:float-left first-letter:mr-3 first-letter:text-[3.5rem] first-letter:font-bold first-letter:leading-[0.8]" : ""
          }`}
          style={i === 0 ? { fontFamily: `"${spec.fonts?.headline ?? "Georgia"}", serif` } : undefined}
        >
          {text}
        </p>
      ))}
    </div>
  );
}
```

Note on first-letter drop cap: Tailwind's `first-letter:` variant maps to CSS `::first-letter` pseudo-element. The drop cap only applies to the first paragraph's first letter.

### Example 3: DesignSpec Pydantic Model (Backend)
```python
# models/design_spec.py
from pydantic import BaseModel, Field

class FontPairing(BaseModel):
    headline: str = "Georgia"
    body: str = "Pretendard"

class ColorPalette(BaseModel):
    primary: str = "#1a1a1a"
    accent: str = "#6366f1"
    background: str = "#ffffff"
    text: str = "#374151"
    muted: str = "#9ca3af"

class DesignSpec(BaseModel):
    """AI-generated design specification for magazine rendering.

    Generated per-curation by Gemini, not persisted.
    """
    fonts: FontPairing = Field(default_factory=FontPairing)
    colors: ColorPalette = Field(default_factory=ColorPalette)
    layout_density: str = "normal"  # compact | normal | spacious
    mood: str = "elegant"
    hero_aspect_ratio: str = "16/9"  # CSS aspect-ratio value
```

### Example 4: design_spec Node
```python
# nodes/design_spec.py
async def design_spec_node(state: EditorialPipelineState) -> dict:
    """Generate design spec from curated topics."""
    curated_topics = state.get("curated_topics") or []
    if not curated_topics:
        return {"design_spec": None}

    keywords = [t.get("keyword", "") for t in curated_topics]
    category = state.get("curation_input", {}).get("category", "fashion")

    service = DesignSpecService(get_genai_client())
    spec = await service.generate(keywords, category)
    return {"design_spec": spec.model_dump()}
```

### Example 5: Pre-loaded Google Fonts Set
```tsx
// layout.tsx - Pre-load curated font set
import { Geist, Geist_Mono } from "next/font/google";
import { Playfair_Display, Noto_Serif_KR, Gothic_A1, Lora } from "next/font/google";

const playfair = Playfair_Display({ subsets: ["latin"], variable: "--font-playfair" });
const notoSerifKr = Noto_Serif_KR({ weight: ["400", "700"], subsets: ["latin"], variable: "--font-noto-serif" });
const gothicA1 = Gothic_A1({ weight: ["400", "500", "700"], subsets: ["latin"], variable: "--font-gothic" });
const lora = Lora({ subsets: ["latin"], variable: "--font-lora" });
```

The design_spec node picks from these pre-loaded fonts. The frontend maps font names to CSS variables.

**Recommended curated font set for Korean fashion magazine:**
- Serif headline: Playfair Display, Lora, Noto Serif KR
- Sans-serif body: Pretendard (system-installed or self-hosted, not on Google Fonts), Gothic A1, Noto Sans KR
- Fallback: Georgia + system sans-serif

**Important note on Pretendard:** Pretendard is NOT available on Google Fonts. It's a Korean font available via CDN (cdn.jsdelivr.net/gh/orioncactus/pretendard). It needs to be loaded differently from `next/font/google`. Options:
1. Use `next/font/local` with downloaded Pretendard files
2. Use `@font-face` in globals.css with CDN URL
3. Substitute with Noto Sans KR (available on Google Fonts) as the "Pretendard-like" option

Recommendation: Use Noto Sans KR from Google Fonts as the default body font (it's the closest widely-available alternative), with Pretendard as an optional self-hosted upgrade later.

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Class component error boundary | Still class component (React 19) | No change | React 19 still has no hooks-based error boundary API |
| `next/image` with `domains` | `next/image` with `remotePatterns` | Next.js 14+ | More granular URL matching, `domains` still works but deprecated |
| `@import url()` for Google Fonts | `next/font/google` | Next.js 13+ | Self-hosted, zero CLS, automatic optimization |
| Tailwind CSS v3 @apply | Tailwind CSS v4 @theme | 2024-2025 | Project already on v4, uses `@theme inline` pattern |

**Deprecated/outdated:**
- `next/image` `domains` config: Use `remotePatterns` instead
- Client-side font loading via `<link>`: Use `next/font/google` for zero-CLS fonts

## Open Questions

1. **Pretendard Font Loading Strategy**
   - What we know: Pretendard is not on Google Fonts. CONTEXT.md specifies "Pretendard 계열" as body font.
   - What's unclear: Whether to self-host Pretendard files or substitute with Noto Sans KR.
   - Recommendation: Use Noto Sans KR as the Google Fonts fallback, document Pretendard as future self-hosted option. The DesignSpec can specify "NotoSansKR" which maps to the pre-loaded font.

2. **design_spec Placement in State: Persisted or Transient?**
   - What we know: CONTEXT.md says "don't persist, generate fresh each time." But the state dict needs the design_spec to flow from the design_spec node through editorial to the frontend.
   - What's unclear: Should design_spec live in `EditorialPipelineState` (LangGraph state) or only in the API response?
   - Recommendation: Add `design_spec: dict | None` to `EditorialPipelineState`. It flows through the pipeline but is NOT saved to the `editorial_contents` Supabase table. The frontend receives it via the API response from the current pipeline state. For already-saved content (no active pipeline), use the default spec.

3. **design_spec Delivery to Frontend**
   - What we know: Current API returns `ContentResponse` with `layout_json: dict`. There's no `design_spec` field.
   - What's unclear: How to pass design_spec to the frontend for live pipeline previews vs. saved content.
   - Recommendation: Add `design_spec` as an optional field on the `MagazineLayout` model (both Python and TypeScript). This way it travels with the layout JSON naturally. Since it's optional with defaults, existing saved content renders fine with the fallback spec.

4. **Error Boundary with Expandable Raw JSON**
   - Claude's Discretion item: Whether error blocks should show raw JSON.
   - Recommendation: YES, add a collapsible "Show raw data" toggle inside the error banner. This helps admin users debug malformed blocks without switching to the JSON tab. Use a simple `<details>/<summary>` HTML element (no JS needed).

5. **Image Blur Placeholder Implementation**
   - Claude's Discretion item: CSS blur vs placeholder image.
   - Recommendation: Use CSS approach. Start with `blur-sm scale-105` Tailwind classes on the `<Image>`, transition to `blur-0 scale-100` on load. For error fallback, use a CSS gradient with the design_spec accent color. No extra library needed.

6. **Drop Cap and Line Height Values**
   - Claude's Discretion item: Specific typography numbers.
   - Recommendation: Drop cap `font-size: 3.5rem`, `line-height: 0.8`, `float: left`, `margin-right: 0.75rem`. Body line-height: `1.8` (spacious for readability). Letter-spacing on headlines: `-0.025em` for tighter, editorial feel.

7. **Google Fonts Range Limitation**
   - Claude's Discretion item: Which fonts the AI can choose from.
   - Recommendation: Limit to a curated set of 6-8 font families pre-loaded in layout.tsx. The design_spec prompt instructs Gemini to choose ONLY from this list. This prevents unbounded font loading.

## Sources

### Primary (HIGH confidence)
- Codebase analysis: All 10 block components, BlockRenderer, detail page, pipeline graph, state, models
- `admin/package.json`: Next.js 15.5.12, React 19.1.0, Tailwind v4, radix-ui 1.4.3
- `admin/src/components/ui/tabs.tsx`: shadcn Tabs already available
- `admin/src/app/layout.tsx`: next/font/google already configured (Geist)
- `src/editorial_ai/state.py`: EditorialPipelineState structure
- `src/editorial_ai/graph.py`: Pipeline topology (curation -> source -> editorial -> enrich -> review)
- `src/editorial_ai/models/layout.py`: MagazineLayout Pydantic model with all block types
- `src/editorial_ai/models/celeb.py`, `product.py`: DB models with image_url fields

### Secondary (MEDIUM confidence)
- Next.js 15 `next/image` docs: remotePatterns config, unoptimized prop, blur placeholder
- React 19 error boundary: Class component approach still required (no hooks API)
- Tailwind CSS v4 `first-letter:` variant: Supported for drop cap styling

### Tertiary (LOW confidence)
- Pretendard font CDN availability: `cdn.jsdelivr.net/gh/orioncactus/pretendard` -- needs validation
- Noto Sans KR as Pretendard substitute: Visual similarity assessment based on training data

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - All tools already in the project, no new dependencies
- Architecture: HIGH - Pattern follows existing codebase conventions exactly
- Backend design_spec node: HIGH - Follows established node/service/model pattern in pipeline
- Frontend image handling: MEDIUM - next/image with external URLs needs runtime validation
- Typography/fonts: MEDIUM - Pretendard availability uncertain, curated font set needs validation
- Pitfalls: HIGH - All identified from direct codebase analysis

**Research date:** 2026-02-26
**Valid until:** 2026-03-28 (30 days - stable stack, no fast-moving deps)
