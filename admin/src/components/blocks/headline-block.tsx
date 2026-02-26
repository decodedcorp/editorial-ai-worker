import type { HeadlineBlock, DesignSpec } from "@/lib/types";

interface HeadlineBlockProps {
  block: HeadlineBlock;
  designSpec?: DesignSpec;
}

const HEADING_STYLES = {
  1: "text-4xl md:text-5xl font-bold tracking-tight leading-tight",
  2: "text-3xl md:text-4xl font-semibold tracking-tight leading-snug",
  3: "text-2xl md:text-3xl font-medium tracking-normal",
} as const;

export function HeadlineBlockComponent({ block, designSpec }: HeadlineBlockProps) {
  const level = block.level ?? 1;
  const Tag = `h${level}` as const;
  const accentColor = designSpec?.color_palette?.accent ?? "hsl(var(--primary))";
  const primaryColor = designSpec?.color_palette?.primary ?? "#1a1a2e";
  const variant = block.layout_variant ?? "default";

  switch (variant) {
    case "full_width_banner":
      return (
        <div
          className="py-10 px-8"
          style={{ backgroundColor: primaryColor }}
        >
          <Tag className="text-4xl md:text-6xl font-bold text-white text-center font-serif"
            style={{ fontFamily: "var(--font-playfair), Georgia, serif" }}
          >
            {block.text ?? ""}
          </Tag>
        </div>
      );

    case "left_aligned_large":
      return (
        <div>
          <Tag
            className="text-6xl md:text-8xl font-bold tracking-tighter leading-[0.9]"
            style={{ fontFamily: "var(--font-playfair), Georgia, serif" }}
          >
            {block.text ?? ""}
          </Tag>
        </div>
      );

    case "overlapping":
      return (
        <div className="relative overflow-hidden py-4">
          <span
            className="absolute inset-0 flex items-center text-7xl md:text-9xl font-bold opacity-[0.07] select-none leading-none whitespace-nowrap overflow-hidden"
            aria-hidden="true"
            style={{ fontFamily: "var(--font-playfair), Georgia, serif" }}
          >
            {block.text ?? ""}
          </span>
          <Tag
            className="relative text-3xl md:text-4xl font-bold"
            style={{ fontFamily: "var(--font-playfair), Georgia, serif" }}
          >
            {block.text ?? ""}
          </Tag>
        </div>
      );

    case "default":
    default: {
      const style = HEADING_STYLES[level] ?? HEADING_STYLES[1];
      return (
        <div>
          <Tag
            className={`${style} font-serif`}
            style={{ fontFamily: "var(--font-playfair), Georgia, serif" }}
          >
            {block.text ?? ""}
          </Tag>
          {level === 1 && (
            <div
              className="mt-3 h-[3px] w-12"
              style={{ backgroundColor: accentColor }}
            />
          )}
        </div>
      );
    }
  }
}
