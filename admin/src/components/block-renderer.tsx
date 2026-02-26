"use client";

import type { LayoutBlock, DesignSpec, AnimationType } from "@/lib/types";
import type { ComponentType } from "react";
import { useRef, useEffect } from "react";

import gsap from "gsap";
import { ScrollTrigger } from "gsap/ScrollTrigger";

import { useDesignSpec } from "@/components/design-spec-provider";
import { BlockErrorBoundary } from "@/components/block-error-boundary";
import { HeroBlockComponent } from "@/components/blocks/hero-block";
import { HeadlineBlockComponent } from "@/components/blocks/headline-block";
import { BodyTextBlockComponent } from "@/components/blocks/body-text-block";
import { ImageGalleryBlockComponent } from "@/components/blocks/image-gallery-block";
import { PullQuoteBlockComponent } from "@/components/blocks/pull-quote-block";
import { ProductShowcaseBlockComponent } from "@/components/blocks/product-showcase-block";
import { CelebFeatureBlockComponent } from "@/components/blocks/celeb-feature-block";
import { DividerBlockComponent } from "@/components/blocks/divider-block";
import { HashtagBarBlockComponent } from "@/components/blocks/hashtag-bar-block";
import { CreditsBlockComponent } from "@/components/blocks/credits-block";

gsap.registerPlugin(ScrollTrigger);

// ---------------------------------------------------------------------------
// Animation presets -- maps AI-decided animation name to GSAP tween vars
// ---------------------------------------------------------------------------

const ANIMATION_PRESETS: Record<string, { from: gsap.TweenVars; to: gsap.TweenVars }> = {
  "fade-up": { from: { opacity: 0, y: 40 }, to: { opacity: 1, y: 0 } },
  "fade-in": { from: { opacity: 0 }, to: { opacity: 1 } },
  "slide-left": { from: { opacity: 0, x: -60 }, to: { opacity: 1, x: 0 } },
  "slide-right": { from: { opacity: 0, x: 60 }, to: { opacity: 1, x: 0 } },
  "scale-in": { from: { opacity: 0, scale: 0.9 }, to: { opacity: 1, scale: 1 } },
  parallax: { from: { opacity: 0, y: 60 }, to: { opacity: 1, y: 0, duration: 1.2 } },
};

// eslint-disable-next-line @typescript-eslint/no-explicit-any
const BLOCK_MAP: Record<string, ComponentType<{ block: any; designSpec?: DesignSpec }>> = {
  hero: HeroBlockComponent,
  headline: HeadlineBlockComponent,
  body_text: BodyTextBlockComponent,
  image_gallery: ImageGalleryBlockComponent,
  pull_quote: PullQuoteBlockComponent,
  product_showcase: ProductShowcaseBlockComponent,
  celeb_feature: CelebFeatureBlockComponent,
  divider: DividerBlockComponent,
  hashtag_bar: HashtagBarBlockComponent,
  credits: CreditsBlockComponent,
};

// ---------------------------------------------------------------------------
// AnimatedBlock -- wraps each block with scroll-triggered GSAP animation
// ---------------------------------------------------------------------------

function AnimatedBlock({
  children,
  index,
  animation,
}: {
  children: React.ReactNode;
  index: number;
  animation?: AnimationType | null;
}) {
  const ref = useRef<HTMLDivElement>(null);

  // First 2 blocks (hero + headline) show immediately, no scroll animation
  const isAboveFold = index < 2;

  useEffect(() => {
    if (!ref.current || isAboveFold) return;

    const animName = animation && animation !== "none" ? animation : "fade-up";
    const preset = ANIMATION_PRESETS[animName] ?? ANIMATION_PRESETS["fade-up"];

    gsap.fromTo(ref.current, preset.from, {
      ...preset.to,
      duration: preset.to.duration ?? 0.7,
      ease: "power2.out",
      delay: Math.max(0, (index - 2) * 0.05),
      scrollTrigger: {
        trigger: ref.current,
        start: "top 90%",
        toggleActions: "play none none none",
      },
    });

    return () => {
      ScrollTrigger.getAll().forEach((t) => {
        if (t.trigger === ref.current) t.kill();
      });
    };
  }, [index, animation, isAboveFold]);

  return <div ref={ref}>{children}</div>;
}

// ---------------------------------------------------------------------------
// Block width helper -- determines wrapper class based on layout_variant
// ---------------------------------------------------------------------------

const FULL_BLEED_VARIANTS = new Set([
  "full_bleed", "parallax", "letterbox", "split_text_left", "split_text_right",
  "full_width_banner", "full_bleed_grid", "full_bleed_single", "staggered_overlap",
  "full_width_background", "full_width_row", "lookbook",
  "hero_collage", "full_bleed_line", "color_band", "gradient_fade",
  "full_width_footer", "floating",
]);

const WIDE_VARIANTS = new Set([
  "wide", "featured_plus_grid", "carousel_cards", "card_row", "filmstrip",
  "centered_large", "oversized_serif", "spotlight",
]);

function getBlockWidthClass(block: LayoutBlock): string {
  const variant = (block as { layout_variant?: string | null }).layout_variant;

  if (variant === "narrow_centered") return "max-w-xl mx-auto";
  if (variant === "sidebar_column") return "max-w-3xl mx-auto";
  if (variant && FULL_BLEED_VARIANTS.has(variant)) return "w-full";
  if (variant && WIDE_VARIANTS.has(variant)) return "max-w-5xl mx-auto";

  // Default: same as before (max-w-3xl centered) -- backward compatible
  return "max-w-3xl mx-auto";
}

// ---------------------------------------------------------------------------
// BlockRenderer
// ---------------------------------------------------------------------------

export function BlockRenderer({ blocks }: { blocks: LayoutBlock[] }) {
  const designSpec = useDesignSpec();

  if (!blocks || blocks.length === 0) {
    return (
      <div className="py-12 text-center text-muted-foreground">
        No blocks to display.
      </div>
    );
  }

  return (
    <article className="w-full space-y-8 py-8">
      {blocks.map((block, i) => {
        const type = (block as { type?: string })?.type;
        const Component = type ? BLOCK_MAP[type] : undefined;

        if (!Component) {
          return (
            <div
              key={i}
              className="max-w-3xl mx-auto rounded border-2 border-dashed border-orange-300 bg-orange-50 p-4 text-sm text-orange-700"
            >
              Unknown block type: {type ?? "undefined"}
            </div>
          );
        }

        const blockAnimation = (block as { animation?: AnimationType | null }).animation;

        return (
          <div key={i} className={getBlockWidthClass(block)}>
            <BlockErrorBoundary blockType={type!} blockData={block}>
              <AnimatedBlock index={i} animation={blockAnimation}>
                <Component block={block} designSpec={designSpec ?? undefined} />
              </AnimatedBlock>
            </BlockErrorBoundary>
          </div>
        );
      })}
    </article>
  );
}
