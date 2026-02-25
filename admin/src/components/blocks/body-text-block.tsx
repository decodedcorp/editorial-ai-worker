import type { BodyTextBlock } from "@/lib/types";

export function BodyTextBlockComponent({ block }: { block: BodyTextBlock }) {
  const paragraphs = block.paragraphs ?? [];

  if (paragraphs.length === 0) {
    return null;
  }

  return (
    <div>
      {paragraphs.map((text, i) => (
        <p key={i} className="mb-4 text-base leading-relaxed text-gray-700 last:mb-0">
          {text}
        </p>
      ))}
    </div>
  );
}
