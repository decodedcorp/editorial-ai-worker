import type { HashtagBarBlock } from "@/lib/types";

export function HashtagBarBlockComponent({ block }: { block: HashtagBarBlock }) {
  const hashtags = block.hashtags ?? [];

  if (hashtags.length === 0) {
    return null;
  }

  return (
    <div className="flex flex-wrap gap-2">
      {hashtags.map((tag, i) => (
        <span
          key={i}
          className="rounded-full bg-gray-100 px-3 py-1 text-sm text-gray-700"
        >
          {tag.startsWith("#") ? tag : `#${tag}`}
        </span>
      ))}
    </div>
  );
}
