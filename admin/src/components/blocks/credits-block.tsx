import type { CreditsBlock } from "@/lib/types";

export function CreditsBlockComponent({ block }: { block: CreditsBlock }) {
  const entries = block.entries ?? [];

  if (entries.length === 0) {
    return null;
  }

  return (
    <div className="grid gap-2 sm:grid-cols-2">
      {entries.map((entry, i) => (
        <div key={i}>
          <p className="text-xs uppercase tracking-wider text-gray-400">
            {entry.role ?? ""}
          </p>
          <p className="text-sm text-gray-600">{entry.name ?? ""}</p>
        </div>
      ))}
    </div>
  );
}
