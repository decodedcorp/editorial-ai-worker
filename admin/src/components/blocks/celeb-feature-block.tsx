import { MagazineImage } from "@/components/magazine-image";
import type { CelebFeatureBlock, DesignSpec } from "@/lib/types";

interface CelebFeatureBlockProps {
  block: CelebFeatureBlock;
  designSpec?: DesignSpec;
}

export function CelebFeatureBlockComponent({ block, designSpec }: CelebFeatureBlockProps) {
  const celebs = block.celebs ?? [];

  if (celebs.length === 0) {
    return null;
  }

  return (
    <div className="grid grid-cols-2 gap-6 sm:grid-cols-3">
      {celebs.map((celeb, i) => (
        <div key={i} className="flex flex-col items-center text-center">
          <div className="size-28 rounded-full overflow-hidden">
            <MagazineImage
              src={celeb.image_url || ""}
              alt={celeb.name}
              aspectRatio="1/1"
              className="rounded-full"
              gradientFrom={designSpec?.color_palette?.primary}
              gradientTo={designSpec?.color_palette?.accent}
            />
          </div>
          <p className="mt-3 font-semibold text-lg">{celeb.name ?? "Unknown"}</p>
          {celeb.description && (
            <p className="mt-1 text-sm text-gray-600">{celeb.description}</p>
          )}
        </div>
      ))}
    </div>
  );
}
