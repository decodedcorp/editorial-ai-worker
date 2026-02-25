import type { DividerBlock } from "@/lib/types";

export function DividerBlockComponent({ block }: { block: DividerBlock }) {
  const style = block.style ?? "line";

  if (style === "space") {
    return <div className="h-8" />;
  }

  if (style === "ornament") {
    return (
      <div className="flex items-center justify-center py-4">
        <span className="text-xl tracking-[0.5em] text-gray-400">***</span>
      </div>
    );
  }

  // Default: line
  return <hr className="border-gray-200" />;
}
