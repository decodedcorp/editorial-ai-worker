import type { CelebFeatureBlock } from "@/lib/types";

export function CelebFeatureBlockComponent({ block }: { block: CelebFeatureBlock }) {
  const celebs = block.celebs ?? [];

  if (celebs.length === 0) {
    return null;
  }

  return (
    <div className="grid grid-cols-2 gap-6 sm:grid-cols-3">
      {celebs.map((celeb, i) => (
        <div key={i} className="flex flex-col items-center text-center">
          <div className="flex size-24 items-center justify-center rounded-full bg-purple-100 text-xs text-purple-600">
            Photo
          </div>
          <p className="mt-3 font-bold">{celeb.name ?? "Unknown"}</p>
          {celeb.description && (
            <p className="mt-1 text-sm text-gray-600">{celeb.description}</p>
          )}
        </div>
      ))}
    </div>
  );
}
