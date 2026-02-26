import { MagazineImage } from "@/components/magazine-image";
import type { ImageGalleryBlock, DesignSpec } from "@/lib/types";

interface ImageGalleryBlockProps {
  block: ImageGalleryBlock;
  designSpec?: DesignSpec;
}

// ---------------------------------------------------------------------------
// Variant: grid (default)
// ---------------------------------------------------------------------------

function GridGallery({ block, designSpec }: ImageGalleryBlockProps) {
  return (
    <div className="grid grid-cols-2 gap-4">
      {block.images.map((img, i) => (
        <div key={i} className="break-inside-avoid">
          <MagazineImage
            src={img.url}
            alt={img.alt || "Gallery image"}
            aspectRatio="1/1"
            gradientFrom={designSpec?.color_palette?.primary}
            gradientTo={designSpec?.color_palette?.accent}
          />
          {img.caption && (
            <p className="text-xs text-muted-foreground italic mt-1.5">{img.caption}</p>
          )}
        </div>
      ))}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Variant: carousel
// ---------------------------------------------------------------------------

function CarouselGallery({ block, designSpec }: ImageGalleryBlockProps) {
  return (
    <div className="flex gap-4 overflow-x-auto pb-2">
      {block.images.map((img, i) => (
        <div key={i} className="flex-none w-64">
          <MagazineImage
            src={img.url}
            alt={img.alt || "Gallery image"}
            aspectRatio="1/1"
            gradientFrom={designSpec?.color_palette?.primary}
            gradientTo={designSpec?.color_palette?.accent}
          />
          {img.caption && (
            <p className="text-xs text-muted-foreground italic mt-1.5">{img.caption}</p>
          )}
        </div>
      ))}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Variant: masonry
// ---------------------------------------------------------------------------

function MasonryGallery({ block, designSpec }: ImageGalleryBlockProps) {
  return (
    <div className="columns-2 gap-4 space-y-4">
      {block.images.map((img, i) => (
        <div key={i} className="break-inside-avoid">
          <MagazineImage
            src={img.url}
            alt={img.alt || "Gallery image"}
            aspectRatio="3/4"
            gradientFrom={designSpec?.color_palette?.primary}
            gradientTo={designSpec?.color_palette?.accent}
          />
          {img.caption && (
            <p className="text-xs text-muted-foreground italic mt-1.5">{img.caption}</p>
          )}
        </div>
      ))}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Variant: full_bleed_grid -- tight grid, no rounded corners, no captions
// ---------------------------------------------------------------------------

function FullBleedGridGallery({ block, designSpec }: ImageGalleryBlockProps) {
  return (
    <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-1">
      {block.images.map((img, i) => (
        <div key={i}>
          <MagazineImage
            src={img.url}
            alt={img.alt || "Gallery image"}
            aspectRatio="1/1"
            className="!rounded-none"
            gradientFrom={designSpec?.color_palette?.primary}
            gradientTo={designSpec?.color_palette?.accent}
          />
        </div>
      ))}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Variant: asymmetric -- first image large, rest in grid
// ---------------------------------------------------------------------------

function AsymmetricGallery({ block, designSpec }: ImageGalleryBlockProps) {
  const [first, ...rest] = block.images;

  return (
    <div className="grid grid-cols-2 gap-3">
      {/* Featured first image spans full width */}
      {first && (
        <div className="col-span-2">
          <MagazineImage
            src={first.url}
            alt={first.alt || "Gallery image"}
            aspectRatio="16/10"
            gradientFrom={designSpec?.color_palette?.primary}
            gradientTo={designSpec?.color_palette?.accent}
          />
          {first.caption && (
            <p className="text-xs text-muted-foreground italic mt-1.5">{first.caption}</p>
          )}
        </div>
      )}
      {/* Remaining images in 2-col grid */}
      {rest.map((img, i) => (
        <div key={i}>
          <MagazineImage
            src={img.url}
            alt={img.alt || "Gallery image"}
            aspectRatio="1/1"
            gradientFrom={designSpec?.color_palette?.primary}
            gradientTo={designSpec?.color_palette?.accent}
          />
          {img.caption && (
            <p className="text-xs text-muted-foreground italic mt-1.5">{img.caption}</p>
          )}
        </div>
      ))}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Variant: full_bleed_single -- each image full width, stacked
// ---------------------------------------------------------------------------

function FullBleedSingleGallery({ block, designSpec }: ImageGalleryBlockProps) {
  return (
    <div className="flex flex-col gap-2">
      {block.images.map((img, i) => (
        <div key={i}>
          <MagazineImage
            src={img.url}
            alt={img.alt || "Gallery image"}
            aspectRatio="16/9"
            className="!rounded-none"
            gradientFrom={designSpec?.color_palette?.primary}
            gradientTo={designSpec?.color_palette?.accent}
          />
          {img.caption && (
            <p className="text-xs text-muted-foreground italic mt-2 px-4">{img.caption}</p>
          )}
        </div>
      ))}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Variant: staggered_overlap -- collage with negative margins
// ---------------------------------------------------------------------------

const STAGGER_CLASSES = [
  "w-[70%] relative z-10",
  "w-[55%] ml-auto -mt-16 relative z-20",
  "w-[60%] -mt-12 relative z-30",
  "w-[50%] ml-auto -mt-14 relative z-40",
  "w-[65%] -mt-10 relative z-50",
] as const;

function StaggeredOverlapGallery({ block, designSpec }: ImageGalleryBlockProps) {
  return (
    <div className="relative py-4">
      {block.images.map((img, i) => (
        <div
          key={i}
          className={`${STAGGER_CLASSES[i % STAGGER_CLASSES.length]} shadow-xl rounded-sm overflow-hidden mb-2`}
        >
          <MagazineImage
            src={img.url}
            alt={img.alt || "Gallery image"}
            aspectRatio="4/3"
            className="!rounded-sm"
            gradientFrom={designSpec?.color_palette?.primary}
            gradientTo={designSpec?.color_palette?.accent}
          />
        </div>
      ))}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Variant: filmstrip -- horizontal cinematic strip
// ---------------------------------------------------------------------------

function FilmstripGallery({ block, designSpec }: ImageGalleryBlockProps) {
  return (
    <div className="flex gap-2 overflow-x-auto pb-3">
      {block.images.map((img, i) => (
        <div key={i} className="flex-none w-[40vw] md:w-[30vw] border-2 border-white rounded-sm overflow-hidden">
          <MagazineImage
            src={img.url}
            alt={img.alt || "Gallery image"}
            aspectRatio="21/9"
            className="!rounded-none"
            gradientFrom={designSpec?.color_palette?.primary}
            gradientTo={designSpec?.color_palette?.accent}
          />
        </div>
      ))}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Main component
// ---------------------------------------------------------------------------

export function ImageGalleryBlockComponent({ block, designSpec }: ImageGalleryBlockProps) {
  const images = block.images ?? [];
  if (images.length === 0) return null;

  // Backward compat: layout_variant takes precedence, falls back to layout_style
  const variant = block.layout_variant ?? block.layout_style ?? "grid";

  switch (variant) {
    case "carousel":
      return <CarouselGallery block={block} designSpec={designSpec} />;
    case "masonry":
      return <MasonryGallery block={block} designSpec={designSpec} />;
    case "full_bleed_grid":
      return <FullBleedGridGallery block={block} designSpec={designSpec} />;
    case "asymmetric":
      return <AsymmetricGallery block={block} designSpec={designSpec} />;
    case "full_bleed_single":
      return <FullBleedSingleGallery block={block} designSpec={designSpec} />;
    case "staggered_overlap":
      return <StaggeredOverlapGallery block={block} designSpec={designSpec} />;
    case "filmstrip":
      return <FilmstripGallery block={block} designSpec={designSpec} />;
    case "grid":
    default:
      return <GridGallery block={block} designSpec={designSpec} />;
  }
}
