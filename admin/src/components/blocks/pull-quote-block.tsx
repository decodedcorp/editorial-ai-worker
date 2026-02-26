import type { PullQuoteBlock, DesignSpec } from "@/lib/types";

interface PullQuoteBlockProps {
  block: PullQuoteBlock;
  designSpec?: DesignSpec;
}

export function PullQuoteBlockComponent({ block, designSpec }: PullQuoteBlockProps) {
  const accentColor = designSpec?.color_palette?.accent ?? "hsl(var(--primary))";

  return (
    <blockquote
      className="border-l-[3px] pl-6 py-2"
      style={{ borderColor: accentColor }}
    >
      <p
        className="text-2xl md:text-3xl italic text-gray-800"
        style={{ fontFamily: "Georgia, serif" }}
      >
        <span className="text-gray-300 select-none" aria-hidden="true">{"\u201C"}</span>
        {block.quote ?? ""}
        <span className="text-gray-300 select-none" aria-hidden="true">{"\u201D"}</span>
      </p>
      {block.attribution && (
        <footer className="mt-3 text-sm tracking-wide uppercase text-muted-foreground">
          &mdash; {block.attribution}
        </footer>
      )}
    </blockquote>
  );
}
