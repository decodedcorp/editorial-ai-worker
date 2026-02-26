"use client";

import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { MagazinePreview } from "@/components/magazine-preview";
import { PipelineTab } from "@/components/pipeline/pipeline-tab";
import type { LayoutBlock, DesignSpec, LogsResponse } from "@/lib/types";

interface ContentTabsProps {
  blocks: LayoutBlock[];
  designSpec: DesignSpec | null;
  layoutJson: unknown;
  logs: LogsResponse | null;
  contentId: string;
  layoutImageBase64?: string | null;
}

export function ContentTabs({
  blocks,
  designSpec,
  layoutJson,
  logs,
  contentId,
  layoutImageBase64,
}: ContentTabsProps) {
  return (
    <Tabs defaultValue="magazine">
      <TabsList>
        <TabsTrigger value="magazine">Magazine</TabsTrigger>
        {layoutImageBase64 && (
          <TabsTrigger value="layout-image">Layout Image</TabsTrigger>
        )}
        <TabsTrigger value="json">JSON</TabsTrigger>
        <TabsTrigger value="pipeline">Pipeline</TabsTrigger>
      </TabsList>

      <TabsContent value="magazine">
        <MagazinePreview blocks={blocks} designSpec={designSpec} />
      </TabsContent>

      {layoutImageBase64 && (
        <TabsContent value="layout-image">
          <div className="space-y-4">
            <div className="rounded-lg border bg-muted/50 p-4">
              <h3 className="text-sm font-medium">Nano Banana Layout Image</h3>
              <p className="mt-1 text-xs text-muted-foreground">
                AI가 생성한 레이아웃 디자인 이미지입니다. 이 이미지를 Vision AI가 파싱하여 블록 구조를 추출합니다.
              </p>
            </div>
            <div className="flex justify-center rounded-lg border bg-white p-4">
              {/* eslint-disable-next-line @next/next/no-img-element */}
              <img
                src={`data:image/png;base64,${layoutImageBase64}`}
                alt="Nano Banana generated layout design"
                className="max-h-[80vh] w-auto rounded shadow-lg"
              />
            </div>
          </div>
        </TabsContent>
      )}

      <TabsContent value="json">
        <pre className="max-h-[80vh] overflow-auto rounded-lg bg-slate-950 p-4 font-mono text-xs text-slate-100">
          {JSON.stringify(layoutJson, null, 2)}
        </pre>
      </TabsContent>

      <TabsContent value="pipeline">
        <PipelineTab logs={logs} contentId={contentId} />
      </TabsContent>
    </Tabs>
  );
}
