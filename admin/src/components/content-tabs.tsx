"use client";

import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { MagazinePreview } from "@/components/magazine-preview";
import type { LayoutBlock, DesignSpec } from "@/lib/types";

interface ContentTabsProps {
  blocks: LayoutBlock[];
  designSpec: DesignSpec | null;
  layoutJson: unknown;
}

export function ContentTabs({
  blocks,
  designSpec,
  layoutJson,
}: ContentTabsProps) {
  return (
    <Tabs defaultValue="magazine">
      <TabsList>
        <TabsTrigger value="magazine">Magazine</TabsTrigger>
        <TabsTrigger value="json">JSON</TabsTrigger>
      </TabsList>

      <TabsContent value="magazine">
        <MagazinePreview blocks={blocks} designSpec={designSpec} />
      </TabsContent>

      <TabsContent value="json">
        <pre className="max-h-[80vh] overflow-auto rounded-lg bg-slate-950 p-4 font-mono text-xs text-slate-100">
          {JSON.stringify(layoutJson, null, 2)}
        </pre>
      </TabsContent>
    </Tabs>
  );
}
