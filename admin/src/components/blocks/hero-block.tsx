import { MagazineImage } from "@/components/magazine-image";
import type { HeroBlock, DesignSpec } from "@/lib/types";

interface HeroBlockProps {
  block: HeroBlock;
  designSpec?: DesignSpec;
}

// ---------------------------------------------------------------------------
// Overlay text -- shared across variants
// ---------------------------------------------------------------------------

function HeroOverlay({
  title,
  subtitle,
  className = "",
  titleClass = "text-4xl md:text-5xl",
  subtitleClass = "text-lg md:text-xl",
}: {
  title?: string | null;
  subtitle?: string | null;
  className?: string;
  titleClass?: string;
  subtitleClass?: string;
}) {
  if (!title && !subtitle) return null;

  return (
    <div className={className}>
      {title && (
        <h1
          className={`font-bold text-white drop-shadow-lg ${titleClass}`}
          style={{ fontFamily: "var(--font-playfair), Georgia, serif" }}
        >
          {title}
        </h1>
      )}
      {subtitle && (
        <p
          className={`mt-3 text-white/90 drop-shadow-md ${subtitleClass}`}
          style={{ fontFamily: "var(--font-playfair), Georgia, serif" }}
        >
          {subtitle}
        </p>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Variant renderers
// ---------------------------------------------------------------------------

/** contained -- default / current behavior */
function ContainedHero({ block, designSpec }: HeroBlockProps) {
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
      <HeroOverlay
        title={block.overlay_title}
        subtitle={block.overlay_subtitle}
        className="absolute inset-0 flex flex-col items-center justify-end bg-gradient-to-t from-black/60 to-transparent p-8"
        titleClass="text-center text-4xl md:text-5xl"
        subtitleClass="text-center text-lg md:text-xl"
      />
    </div>
  );
}

/** full_bleed -- edge-to-edge, 90vh tall */
function FullBleedHero({ block, designSpec }: HeroBlockProps) {
  return (
    <div className="relative w-full min-h-[90vh] overflow-hidden">
      <MagazineImage
        src={block.image_url}
        alt={block.overlay_title || "Hero image"}
        className="absolute inset-0 h-full w-full !rounded-none"
        aspectRatio="auto"
        gradientFrom={designSpec?.color_palette?.primary}
        gradientTo={designSpec?.color_palette?.accent}
        priority
      />
      <HeroOverlay
        title={block.overlay_title}
        subtitle={block.overlay_subtitle}
        className="absolute inset-0 flex flex-col items-center justify-end bg-gradient-to-t from-black/70 via-black/20 to-transparent p-8 pb-16"
        titleClass="text-center text-5xl md:text-7xl"
        subtitleClass="text-center text-xl md:text-2xl"
      />
    </div>
  );
}

/** split_text_left -- dark text panel left, image right */
function SplitTextLeftHero({ block, designSpec }: HeroBlockProps) {
  const bgColor = designSpec?.color_palette?.primary ?? "#111827";

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 min-h-[70vh] overflow-hidden">
      {/* Text panel */}
      <div
        className="flex flex-col justify-center p-8 md:p-12"
        style={{ backgroundColor: bgColor }}
      >
        <HeroOverlay
          title={block.overlay_title}
          subtitle={block.overlay_subtitle}
          titleClass="text-3xl md:text-5xl"
          subtitleClass="text-base md:text-lg"
        />
      </div>
      {/* Image panel */}
      <div className="relative min-h-[40vh] md:min-h-0">
        <MagazineImage
          src={block.image_url}
          alt={block.overlay_title || "Hero image"}
          className="absolute inset-0 h-full w-full !rounded-none"
          aspectRatio="auto"
          gradientFrom={designSpec?.color_palette?.primary}
          gradientTo={designSpec?.color_palette?.accent}
          priority
        />
      </div>
    </div>
  );
}

/** split_text_right -- image left, dark text panel right */
function SplitTextRightHero({ block, designSpec }: HeroBlockProps) {
  const bgColor = designSpec?.color_palette?.primary ?? "#111827";

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 min-h-[70vh] overflow-hidden">
      {/* Image panel */}
      <div className="relative min-h-[40vh] md:min-h-0 md:order-1">
        <MagazineImage
          src={block.image_url}
          alt={block.overlay_title || "Hero image"}
          className="absolute inset-0 h-full w-full !rounded-none"
          aspectRatio="auto"
          gradientFrom={designSpec?.color_palette?.primary}
          gradientTo={designSpec?.color_palette?.accent}
          priority
        />
      </div>
      {/* Text panel */}
      <div
        className="flex flex-col justify-center p-8 md:p-12 md:order-2"
        style={{ backgroundColor: bgColor }}
      >
        <HeroOverlay
          title={block.overlay_title}
          subtitle={block.overlay_subtitle}
          titleClass="text-3xl md:text-5xl"
          subtitleClass="text-base md:text-lg"
        />
      </div>
    </div>
  );
}

/** parallax -- fixed-feel background with centered text */
function ParallaxHero({ block, designSpec }: HeroBlockProps) {
  return (
    <div className="relative w-full min-h-[85vh] overflow-hidden">
      {/* Image with will-change for smooth scroll parallax */}
      <div className="absolute inset-0 will-change-transform">
        <MagazineImage
          src={block.image_url}
          alt={block.overlay_title || "Hero image"}
          className="absolute inset-0 h-[120%] w-full !rounded-none -top-[10%]"
          aspectRatio="auto"
          gradientFrom={designSpec?.color_palette?.primary}
          gradientTo={designSpec?.color_palette?.accent}
          priority
        />
      </div>
      <HeroOverlay
        title={block.overlay_title}
        subtitle={block.overlay_subtitle}
        className="absolute inset-0 flex flex-col items-center justify-center bg-black/30 p-8"
        titleClass="text-center text-5xl md:text-7xl font-bold"
        subtitleClass="text-center text-xl md:text-2xl"
      />
    </div>
  );
}

/** letterbox -- cinematic 21:9 cropped with centered text */
function LetterboxHero({ block, designSpec }: HeroBlockProps) {
  return (
    <div className="relative w-full overflow-hidden aspect-[21/9]">
      <MagazineImage
        src={block.image_url}
        alt={block.overlay_title || "Hero image"}
        className="absolute inset-0 h-full w-full !rounded-none"
        aspectRatio="auto"
        gradientFrom={designSpec?.color_palette?.primary}
        gradientTo={designSpec?.color_palette?.accent}
        priority
      />
      <HeroOverlay
        title={block.overlay_title}
        subtitle={block.overlay_subtitle}
        className="absolute inset-0 flex flex-col items-center justify-center bg-black/40 p-8"
        titleClass="text-center text-4xl md:text-6xl tracking-wider uppercase"
        subtitleClass="text-center text-lg md:text-xl tracking-wide uppercase"
      />
    </div>
  );
}

// ---------------------------------------------------------------------------
// Main component
// ---------------------------------------------------------------------------

export function HeroBlockComponent({ block, designSpec }: HeroBlockProps) {
  const variant = block.layout_variant ?? "contained";

  switch (variant) {
    case "full_bleed":
      return <FullBleedHero block={block} designSpec={designSpec} />;
    case "split_text_left":
      return <SplitTextLeftHero block={block} designSpec={designSpec} />;
    case "split_text_right":
      return <SplitTextRightHero block={block} designSpec={designSpec} />;
    case "parallax":
      return <ParallaxHero block={block} designSpec={designSpec} />;
    case "letterbox":
      return <LetterboxHero block={block} designSpec={designSpec} />;
    case "contained":
    default:
      return <ContainedHero block={block} designSpec={designSpec} />;
  }
}
