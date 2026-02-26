import type { DividerBlock, DesignSpec } from "@/lib/types";

interface DividerBlockProps {
  block: DividerBlock;
  designSpec?: DesignSpec;
}

export function DividerBlockComponent({ block, designSpec }: DividerBlockProps) {
  // layout_variant takes priority; fall back to legacy style field for backward compat
  const variant = block.layout_variant ?? block.style ?? "line";

  switch (variant) {
    case "space":
      return <div className="h-12" />;

    case "ornament":
      return (
        <div className="flex items-center justify-center py-4">
          <span className="text-lg tracking-[1em] text-gray-300">{"\u00B7 \u00B7 \u00B7"}</span>
        </div>
      );

    case "full_bleed_line":
      return <hr className="border-t border-gray-300 w-full" />;

    case "color_band": {
      const accentColor = designSpec?.color_palette?.accent;
      return accentColor ? (
        <div className="h-2 w-full" style={{ backgroundColor: accentColor }} />
      ) : (
        <div className="h-2 w-full bg-gray-200" />
      );
    }

    case "gradient_fade":
      return (
        <div className="h-16 w-full bg-gradient-to-b from-transparent via-gray-100 to-transparent" />
      );

    case "line":
    default:
      return <hr className="border-t border-gray-200" />;
  }
}
