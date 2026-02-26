import { MagazineImage } from "@/components/magazine-image";
import type { ImageGalleryBlock, DesignSpec } from "@/lib/types";

interface ImageGalleryBlockProps {
  block: ImageGalleryBlock;
  designSpec?: DesignSpec;
}

export function ImageGalleryBlockComponent({ block, designSpec }: ImageGalleryBlockProps) {
  const images = block.images ?? [];
  const layoutStyle = block.layout_style ?? "grid";

  if (images.length === 0) {
    return null;
  }

  const gridClass =
    layoutStyle === "carousel"
      ? "flex gap-4 overflow-x-auto pb-2"
      : layoutStyle === "masonry"
        ? "columns-2 gap-4 space-y-4"
        : "grid grid-cols-2 gap-4";

  const aspectRatio = layoutStyle === "masonry" ? "3/4" : "1/1";

  return (
    <div className={gridClass}>
      {images.map((img, i) => (
        <div
          key={i}
          className={
            layoutStyle === "carousel" ? "flex-none w-64" : "break-inside-avoid"
          }
        >
          <MagazineImage
            src={img.url}
            alt={img.alt || "Gallery image"}
            aspectRatio={aspectRatio}
            gradientFrom={designSpec?.color_palette?.primary}
            gradientTo={designSpec?.color_palette?.accent}
          />
          {img.caption && (
            <p className="text-xs text-muted-foreground italic mt-1.5">
              {img.caption}
            </p>
          )}
        </div>
      ))}
    </div>
  );
}
