import { MagazineImage } from "@/components/magazine-image";
import type { CelebFeatureBlock, CelebItem, DesignSpec } from "@/lib/types";

interface CelebFeatureBlockProps {
  block: CelebFeatureBlock;
  designSpec?: DesignSpec;
}

export function CelebFeatureBlockComponent({ block, designSpec }: CelebFeatureBlockProps) {
  const celebs = block.celebs ?? [];

  if (celebs.length === 0) {
    return null;
  }

  const variant = block.layout_variant ?? "grid";

  switch (variant) {
    case "spotlight":
      return (
        <div className="space-y-8">
          {/* Spotlight: first celeb large */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
            <div className="overflow-hidden rounded-lg">
              <MagazineImage
                src={celebs[0].image_url || ""}
                alt={celebs[0].name}
                aspectRatio="3/4"
                className="rounded-lg"
                gradientFrom={designSpec?.color_palette?.primary}
                gradientTo={designSpec?.color_palette?.accent}
              />
            </div>
            <div className="flex flex-col justify-center">
              <h3 className="text-3xl font-bold">{celebs[0].name ?? "Unknown"}</h3>
              {celebs[0].description && (
                <p className="mt-4 text-lg leading-relaxed text-gray-600">{celebs[0].description}</p>
              )}
            </div>
          </div>
          {/* Additional celebs as small list */}
          {celebs.length > 1 && (
            <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
              {celebs.slice(1).map((celeb, i) => (
                <div key={i} className="flex flex-col items-center text-center">
                  <div className="size-16 rounded-full overflow-hidden">
                    <MagazineImage
                      src={celeb.image_url || ""}
                      alt={celeb.name}
                      aspectRatio="1/1"
                      className="rounded-full"
                      gradientFrom={designSpec?.color_palette?.primary}
                      gradientTo={designSpec?.color_palette?.accent}
                    />
                  </div>
                  <p className="mt-2 font-medium text-sm">{celeb.name ?? "Unknown"}</p>
                </div>
              ))}
            </div>
          )}
        </div>
      );

    case "card_row":
      return (
        <div className="flex gap-4 overflow-x-auto pb-3">
          {celebs.map((celeb, i) => (
            <div key={i} className="flex-none w-56 relative overflow-hidden rounded-lg">
              <MagazineImage
                src={celeb.image_url || ""}
                alt={celeb.name}
                aspectRatio="2/3"
                className="rounded-lg"
                gradientFrom={designSpec?.color_palette?.primary}
                gradientTo={designSpec?.color_palette?.accent}
              />
              <div className="absolute bottom-0 inset-x-0 bg-gradient-to-t from-black/70 to-transparent p-4">
                <p className="text-white font-semibold">{celeb.name ?? "Unknown"}</p>
                {celeb.description && (
                  <p className="text-white/80 text-xs mt-1 line-clamp-2">{celeb.description}</p>
                )}
              </div>
            </div>
          ))}
        </div>
      );

    case "minimal_list":
      return (
        <div className="divide-y">
          {celebs.map((celeb, i) => (
            <div key={i} className="flex items-center gap-4 py-3">
              <div className="size-10 rounded-full overflow-hidden flex-none">
                <MagazineImage
                  src={celeb.image_url || ""}
                  alt={celeb.name}
                  aspectRatio="1/1"
                  className="rounded-full"
                  gradientFrom={designSpec?.color_palette?.primary}
                  gradientTo={designSpec?.color_palette?.accent}
                />
              </div>
              <div>
                <p className="font-semibold">{celeb.name ?? "Unknown"}</p>
                {celeb.description && (
                  <p className="text-sm text-gray-600">{celeb.description}</p>
                )}
              </div>
            </div>
          ))}
        </div>
      );

    case "hero_collage": {
      // Position configs for up to 5 celebs in an overlapping collage
      const positions = [
        "w-[50%] top-0 left-0 z-10",
        "w-[45%] top-[15%] right-0 z-20",
        "w-[40%] bottom-0 left-[20%] z-[30]",
        "w-[35%] top-[5%] left-[55%] z-[15]",
        "w-[38%] bottom-[5%] right-[5%] z-[25]",
      ];
      return (
        <div className="space-y-4">
          <div className="relative h-[400px] md:h-[500px]">
            {celebs.slice(0, 5).map((celeb, i) => (
              <div
                key={i}
                className={`absolute shadow-xl rounded-sm overflow-hidden ${positions[i]}`}
              >
                <MagazineImage
                  src={celeb.image_url || ""}
                  alt={celeb.name}
                  aspectRatio="3/4"
                  className="rounded-sm"
                  gradientFrom={designSpec?.color_palette?.primary}
                  gradientTo={designSpec?.color_palette?.accent}
                />
              </div>
            ))}
          </div>
          {/* Names listed below collage */}
          <div className="flex flex-wrap gap-x-6 gap-y-1 justify-center">
            {celebs.map((celeb, i) => (
              <span key={i} className="text-sm font-medium text-gray-700">
                {celeb.name ?? "Unknown"}
              </span>
            ))}
          </div>
        </div>
      );
    }

    case "grid":
    default:
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
}
