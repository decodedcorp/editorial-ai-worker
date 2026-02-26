import type { HashtagBarBlock, DesignSpec } from "@/lib/types";

interface HashtagBarBlockProps {
  block: HashtagBarBlock;
  designSpec?: DesignSpec;
}

export function HashtagBarBlockComponent({ block }: HashtagBarBlockProps) {
  const hashtags = block.hashtags ?? [];

  if (hashtags.length === 0) {
    return null;
  }

  return (
    <div className="flex flex-wrap gap-2">
      {hashtags.map((tag, i) => (
        <span
          key={i}
          className="rounded-full border border-gray-200 bg-gray-50 hover:bg-gray-100 transition-colors px-4 py-1.5 text-xs font-medium tracking-wide uppercase text-gray-700"
        >
          {tag.startsWith("#") ? tag : `#${tag}`}
        </span>
      ))}
    </div>
  );
}
