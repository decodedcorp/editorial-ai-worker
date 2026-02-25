import type { ImageGalleryBlock } from "@/lib/types";

export function ImageGalleryBlockComponent({ block }: { block: ImageGalleryBlock }) {
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

  return (
    <div className={gridClass}>
      {images.map((img, i) => (
        <div
          key={i}
          className={
            layoutStyle === "carousel" ? "flex-none w-64" : "break-inside-avoid"
          }
        >
          <div className="flex aspect-square items-center justify-center rounded bg-slate-200 text-sm text-slate-500">
            {img.alt || "Image"}
          </div>
          {img.caption && (
            <p className="mt-1 text-xs text-gray-500">{img.caption}</p>
          )}
        </div>
      ))}
    </div>
  );
}
