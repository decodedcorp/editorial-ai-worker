import type { DividerBlock, DesignSpec } from "@/lib/types";

interface DividerBlockProps {
  block: DividerBlock;
  designSpec?: DesignSpec;
}

export function DividerBlockComponent({ block }: DividerBlockProps) {
  const style = block.style ?? "line";

  if (style === "space") {
    return <div className="h-12" />;
  }

  if (style === "ornament") {
    return (
      <div className="flex items-center justify-center py-4">
        <span className="text-lg tracking-[1em] text-gray-300">{"\u00B7 \u00B7 \u00B7"}</span>
      </div>
    );
  }

  // Default: line
  return <hr className="border-t border-gray-200" />;
}
