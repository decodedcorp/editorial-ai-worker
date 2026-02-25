import type { HeadlineBlock } from "@/lib/types";

const HEADING_STYLES = {
  1: "text-4xl font-bold",
  2: "text-3xl font-semibold",
  3: "text-2xl font-medium",
} as const;

export function HeadlineBlockComponent({ block }: { block: HeadlineBlock }) {
  const level = block.level ?? 1;
  const style = HEADING_STYLES[level] ?? HEADING_STYLES[1];
  const Tag = `h${level}` as const;

  return (
    <Tag className={`${style} font-serif`} style={{ fontFamily: "Georgia, serif" }}>
      {block.text ?? ""}
    </Tag>
  );
}
