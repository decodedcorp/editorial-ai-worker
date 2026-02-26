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
  const style = HEADING_STYLES[level] ?? HEADING_STYLES[1];
  const Tag = `h${level}` as const;
  const accentColor = designSpec?.color_palette?.accent ?? "hsl(var(--primary))";

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
