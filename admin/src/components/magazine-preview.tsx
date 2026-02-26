"use client";

import { DesignSpecProvider } from "@/components/design-spec-provider";
import { BlockRenderer } from "@/components/block-renderer";
import type { LayoutBlock, DesignSpec } from "@/lib/types";

interface MagazinePreviewProps {
  blocks: LayoutBlock[];
  designSpec: DesignSpec | null;
}

export function MagazinePreview({ blocks, designSpec }: MagazinePreviewProps) {
  return (
    <DesignSpecProvider designSpec={designSpec}>
      <div
        className="rounded-lg border bg-white p-8 md:p-12"
        style={{
          backgroundColor: designSpec?.color_palette?.background ?? "#ffffff",
        }}
      >
        <BlockRenderer blocks={blocks} />
      </div>
    </DesignSpecProvider>
  );
}
