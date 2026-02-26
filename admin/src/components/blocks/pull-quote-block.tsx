import type { PullQuoteBlock, DesignSpec } from "@/lib/types";

interface PullQuoteBlockProps {
  block: PullQuoteBlock;
  designSpec?: DesignSpec;
}

export function PullQuoteBlockComponent({ block, designSpec }: PullQuoteBlockProps) {
  const accentColor = designSpec?.color_palette?.accent ?? "hsl(var(--primary))";
  const variant = block.layout_variant ?? "default";

  switch (variant) {
    case "centered_large":
      return (
        <blockquote className="text-center py-12">
          <span
            className="block text-6xl leading-none text-gray-300 select-none"
            aria-hidden="true"
          >
            {"\u201C"}
          </span>
          <p
            className="text-3xl md:text-4xl italic text-gray-800 mt-2 max-w-3xl mx-auto"
            style={{ fontFamily: "Georgia, serif" }}
          >
            {block.quote ?? ""}
          </p>
          <span
            className="block text-6xl leading-none text-gray-300 select-none mt-2"
            aria-hidden="true"
          >
            {"\u201D"}
          </span>
          {block.attribution && (
            <footer className="mt-4 text-sm tracking-wide uppercase text-muted-foreground">
              &mdash; {block.attribution}
            </footer>
          )}
        </blockquote>
      );

    case "full_width_background":
      return (
        <blockquote
          className="py-12 px-8 text-center"
          style={{ backgroundColor: accentColor + "15" }}
        >
          <p
            className="text-2xl md:text-3xl italic text-gray-800 max-w-4xl mx-auto"
            style={{ fontFamily: "Georgia, serif" }}
          >
            <span className="text-gray-400 select-none" aria-hidden="true">{"\u201C"}</span>
            {block.quote ?? ""}
            <span className="text-gray-400 select-none" aria-hidden="true">{"\u201D"}</span>
          </p>
          {block.attribution && (
            <footer className="mt-4 text-sm tracking-wide uppercase text-muted-foreground">
              &mdash; {block.attribution}
            </footer>
          )}
        </blockquote>
      );

    case "sidebar":
      return (
        <blockquote
          className="float-right w-64 ml-6 mb-4 pl-4 border-l-2"
          style={{ borderColor: accentColor }}
        >
          <p
            className="text-lg italic text-gray-700"
            style={{ fontFamily: "Georgia, serif" }}
          >
            {block.quote ?? ""}
          </p>
          {block.attribution && (
            <footer className="mt-2 text-xs tracking-wide uppercase text-muted-foreground">
              &mdash; {block.attribution}
            </footer>
          )}
        </blockquote>
      );

    case "oversized_serif":
      return (
        <blockquote className="py-8">
          <p
            className="text-5xl md:text-6xl leading-tight text-gray-700"
            style={{ fontFamily: "Georgia, 'Times New Roman', serif" }}
          >
            {block.quote ?? ""}
          </p>
          {block.attribution && (
            <footer className="mt-4 text-xs tracking-[0.2em] uppercase text-muted-foreground">
              {block.attribution}
            </footer>
          )}
        </blockquote>
      );

    case "default":
    default:
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
}
