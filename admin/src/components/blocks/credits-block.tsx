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

  const variant = block.layout_variant ?? "default";

  switch (variant) {
    case "full_width_footer":
      return (
        <div className="bg-gray-900 text-white py-10 px-8">
          <p className="text-[10px] uppercase tracking-[0.15em] text-gray-400 font-medium mb-4">
            Credits
          </p>
          <div className="grid gap-4 sm:grid-cols-2 md:grid-cols-3">
            {entries.map((entry, i) => (
              <div key={i}>
                <p className="text-gray-500 text-[10px] uppercase tracking-[0.15em] font-medium">
                  {entry.role ?? ""}
                </p>
                <p className="text-gray-200 text-sm">{entry.name ?? ""}</p>
              </div>
            ))}
          </div>
        </div>
      );

    case "inline":
      return (
        <div className="text-xs text-gray-400 text-center">
          {entries
            .map((entry) => `${entry.role ?? ""}: ${entry.name ?? ""}`)
            .join(" / ")}
        </div>
      );

    case "sidebar_column":
      return (
        <div className="ml-auto max-w-[200px] text-right">
          {entries.map((entry, i) => (
            <div key={i} className="mb-2">
              <p className="text-[10px] uppercase tracking-[0.15em] text-gray-400 font-medium">
                {entry.role ?? ""}
              </p>
              <p className="text-xs text-gray-600">{entry.name ?? ""}</p>
            </div>
          ))}
        </div>
      );

    case "default":
    default:
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
}
