import { MagazineImage } from "@/components/magazine-image";
import type { HeroBlock, DesignSpec } from "@/lib/types";

interface HeroBlockProps {
  block: HeroBlock;
  designSpec?: DesignSpec;
}

export function HeroBlockComponent({ block, designSpec }: HeroBlockProps) {
  const aspectRatio = designSpec?.hero_aspect_ratio ?? "16/9";

  return (
    <div className="relative w-full overflow-hidden rounded-lg">
      <MagazineImage
        src={block.image_url}
        alt={block.overlay_title || "Hero image"}
        aspectRatio={aspectRatio}
        gradientFrom={designSpec?.color_palette?.primary}
        gradientTo={designSpec?.color_palette?.accent}
        priority
      />

      {(block.overlay_title || block.overlay_subtitle) && (
        <div className="absolute inset-0 flex flex-col items-center justify-end bg-gradient-to-t from-black/60 to-transparent p-8">
          {block.overlay_title && (
            <h1
              className="text-center text-4xl md:text-5xl font-bold text-white drop-shadow-lg"
              style={{ fontFamily: "var(--font-playfair), Georgia, serif" }}
            >
              {block.overlay_title}
            </h1>
          )}
          {block.overlay_subtitle && (
            <p
              className="mt-3 text-center text-lg md:text-xl text-white/90 drop-shadow-md"
              style={{ fontFamily: "var(--font-playfair), Georgia, serif" }}
            >
              {block.overlay_subtitle}
            </p>
          )}
        </div>
      )}
    </div>
  );
}
