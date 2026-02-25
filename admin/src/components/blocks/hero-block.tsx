import type { HeroBlock } from "@/lib/types";

export function HeroBlockComponent({ block }: { block: HeroBlock }) {
  return (
    <div className="relative aspect-video w-full overflow-hidden rounded-lg bg-slate-200">
      <div className="flex h-full items-center justify-center text-sm text-slate-500">
        Hero Image
      </div>
      {(block.overlay_title || block.overlay_subtitle) && (
        <div className="absolute inset-0 flex flex-col items-center justify-end bg-black/40 p-8">
          {block.overlay_title && (
            <h1 className="text-center text-3xl font-bold text-white">
              {block.overlay_title}
            </h1>
          )}
          {block.overlay_subtitle && (
            <p className="mt-2 text-center text-lg text-white/90">
              {block.overlay_subtitle}
            </p>
          )}
        </div>
      )}
    </div>
  );
}
