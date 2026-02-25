import type { LayoutBlock } from "@/lib/types";
import type { ComponentType } from "react";

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

// eslint-disable-next-line @typescript-eslint/no-explicit-any
const BLOCK_MAP: Record<string, ComponentType<{ block: any }>> = {
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

export function BlockRenderer({ blocks }: { blocks: LayoutBlock[] }) {
  if (!blocks || blocks.length === 0) {
    return (
      <div className="py-12 text-center text-muted-foreground">
        No blocks to display.
      </div>
    );
  }

  return (
    <article className="mx-auto max-w-3xl space-y-8 py-8">
      {blocks.map((block, i) => {
        const type = (block as { type?: string })?.type;
        const Component = type ? BLOCK_MAP[type] : undefined;

        if (!Component) {
          return (
            <div
              key={i}
              className="rounded border-2 border-dashed border-orange-300 bg-orange-50 p-4 text-sm text-orange-700"
            >
              Unknown block type: {type ?? "undefined"}
            </div>
          );
        }

        return <Component key={i} block={block} />;
      })}
    </article>
  );
}
