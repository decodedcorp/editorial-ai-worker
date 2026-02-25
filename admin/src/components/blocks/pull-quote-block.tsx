import type { PullQuoteBlock } from "@/lib/types";

export function PullQuoteBlockComponent({ block }: { block: PullQuoteBlock }) {
  return (
    <blockquote className="border-l-4 border-primary pl-6">
      <p
        className="text-xl italic text-gray-800"
        style={{ fontFamily: "Georgia, serif" }}
      >
        {block.quote ?? ""}
      </p>
      {block.attribution && (
        <footer className="mt-2 text-sm text-gray-500">
          &mdash; {block.attribution}
        </footer>
      )}
    </blockquote>
  );
}
