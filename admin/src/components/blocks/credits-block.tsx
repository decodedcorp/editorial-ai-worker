import type { CreditsBlock, DesignSpec } from "@/lib/types";

interface CreditsBlockProps {
  block: CreditsBlock;
  designSpec?: DesignSpec;
}

export function CreditsBlockComponent({ block }: CreditsBlockProps) {
  const entries = block.entries ?? [];

  if (entries.length === 0) {
    return null;
  }

  return (
    <div className="border-t pt-6 mt-4">
      <p className="text-[10px] uppercase tracking-[0.15em] text-gray-400 font-medium mb-4">
        Credits
      </p>
      <div className="grid gap-2 sm:grid-cols-2">
        {entries.map((entry, i) => (
          <div key={i}>
            <p className="text-[10px] uppercase tracking-[0.15em] text-gray-400 font-medium">
              {entry.role ?? ""}
            </p>
            <p className="text-sm text-gray-600">{entry.name ?? ""}</p>
          </div>
        ))}
      </div>
    </div>
  );
}
