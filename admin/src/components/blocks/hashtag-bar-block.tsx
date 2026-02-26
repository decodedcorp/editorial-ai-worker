import type { HashtagBarBlock, DesignSpec } from "@/lib/types";

interface HashtagBarBlockProps {
  block: HashtagBarBlock;
  designSpec?: DesignSpec;
}

const FONT_SIZES = ["text-xs", "text-sm", "text-base", "text-lg"] as const;
const OPACITIES = ["opacity-70", "opacity-80", "opacity-90", "opacity-100"] as const;

export function HashtagBarBlockComponent({ block, designSpec }: HashtagBarBlockProps) {
  const hashtags = block.hashtags ?? [];

  if (hashtags.length === 0) {
    return null;
  }

  const variant = block.layout_variant ?? "default";
  const formatTag = (tag: string) => (tag.startsWith("#") ? tag : `#${tag}`);

  switch (variant) {
    case "full_width_banner": {
      const accentColor = designSpec?.color_palette?.accent;
      const bgClass = accentColor ? "" : "bg-gray-100";
      return (
        <div
          className={`py-6 px-8 flex flex-wrap justify-center gap-3 ${bgClass}`}
          style={accentColor ? { backgroundColor: `${accentColor}15` } : undefined}
        >
          {hashtags.map((tag, i) => (
            <span
              key={i}
              className="text-sm font-medium text-gray-700"
            >
              {formatTag(tag)}
            </span>
          ))}
        </div>
      );
    }

    case "minimal_inline":
      return (
        <div className="text-sm text-gray-500 text-center">
          {hashtags.map((tag) => formatTag(tag)).join(" / ")}
        </div>
      );

    case "floating":
      return (
        <div className="flex flex-wrap justify-center gap-4 py-6">
          {hashtags.map((tag, i) => (
            <span
              key={i}
              className={`${FONT_SIZES[i % FONT_SIZES.length]} ${OPACITIES[i % OPACITIES.length]} font-medium text-gray-700`}
            >
              {formatTag(tag)}
            </span>
          ))}
        </div>
      );

    case "default":
    default:
      return (
        <div className="flex flex-wrap gap-2">
          {hashtags.map((tag, i) => (
            <span
              key={i}
              className="rounded-full border border-gray-200 bg-gray-50 hover:bg-gray-100 transition-colors px-4 py-1.5 text-xs font-medium tracking-wide uppercase text-gray-700"
            >
              {formatTag(tag)}
            </span>
          ))}
        </div>
      );
  }
}
