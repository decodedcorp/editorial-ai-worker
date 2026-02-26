import { NextRequest, NextResponse } from "next/server";
import { API_BASE_URL, ADMIN_API_KEY, DEMO_MODE } from "@/config";
import { getDemoItems } from "@/lib/demo-data";
import { estimateCost } from "@/components/pipeline/cost-utils";
import type { ContentItem } from "@/lib/types";
import fs from "fs";
import path from "path";

const LOCAL_CONTENTS_DIR = path.join(process.cwd(), "..", "data", "contents");

/**
 * Recursively collects all *.json file paths under the given directory.
 */
function collectJsonFiles(dir: string): string[] {
  const result: string[] = [];
  try {
    const entries = fs.readdirSync(dir, { withFileTypes: true });
    for (const entry of entries) {
      const fullPath = path.join(dir, entry.name);
      if (entry.isDirectory()) {
        result.push(...collectJsonFiles(fullPath));
      } else if (entry.isFile() && entry.name.endsWith(".json")) {
        result.push(fullPath);
      }
    }
  } catch {
    // ignore read errors
  }
  return result;
}

function loadLocalContents(): ContentItem[] {
  if (!fs.existsSync(LOCAL_CONTENTS_DIR)) return [];
  const files = collectJsonFiles(LOCAL_CONTENTS_DIR);
  const seen = new Set<string>();
  const items: ContentItem[] = [];
  for (const filePath of files) {
    try {
      const raw = fs.readFileSync(filePath, "utf-8");
      const item = JSON.parse(raw) as ContentItem;
      // Deduplicate by id (top-level files take precedence over subdirectory ones)
      if (item.id && !seen.has(item.id)) {
        seen.add(item.id);
        // Exclude heavy base64 image from list response
        const { layout_image_base64: _, ...lightweight } = item as ContentItem & { layout_image_base64?: string };
        items.push(lightweight as ContentItem);
      }
    } catch {
      // skip invalid files
    }
  }
  items.sort((a, b) => (b.created_at || "").localeCompare(a.created_at || ""));
  return items;
}

export async function GET(request: NextRequest) {
  const { searchParams } = request.nextUrl;

  // Try local JSON files first (pipeline test mode)
  const localItems = loadLocalContents();
  if (localItems.length > 0) {
    const status = searchParams.get("status") || undefined;
    const limit = parseInt(searchParams.get("limit") || "20", 10);
    const offset = parseInt(searchParams.get("offset") || "0", 10);
    let filtered = localItems;
    if (status) {
      filtered = filtered.filter((i) => i.status === status);
    }
    const paged = filtered.slice(offset, offset + limit);
    const enriched = paged.map((item) => ({
      ...item,
      pipeline_summary: null,
    }));
    return NextResponse.json({ items: enriched, total: filtered.length });
  }

  if (DEMO_MODE) {
    const status = searchParams.get("status") || undefined;
    const limit = parseInt(searchParams.get("limit") || "20", 10);
    const offset = parseInt(searchParams.get("offset") || "0", 10);
    const items = getDemoItems(status);
    const paged = items.slice(offset, offset + limit);
    // Demo items get null summary
    const enriched = paged.map((item: ContentItem) => ({
      ...item,
      pipeline_summary: null,
    }));
    return NextResponse.json({ items: enriched, total: items.length });
  }

  const url = new URL("/api/contents", API_BASE_URL);

  // Forward supported query params
  for (const key of ["status", "limit", "offset"]) {
    const value = searchParams.get(key);
    if (value) {
      url.searchParams.set(key, value);
    }
  }

  const res = await fetch(url.toString(), {
    cache: "no-store",
    headers: {
      "X-API-Key": ADMIN_API_KEY,
    },
  });

  if (!res.ok) {
    const data = await res.json();
    return NextResponse.json(data, { status: res.status });
  }

  const data = await res.json();
  const items = data.items ?? [];

  // Fetch log summaries in parallel for all items (server-side, no N+1 from client)
  const summaries = await Promise.all(
    items.map(async (item: { id: string }) => {
      try {
        const logsRes = await fetch(
          `${API_BASE_URL}/api/contents/${item.id}/logs?include_io=false`,
          {
            cache: "no-store",
            headers: { "X-API-Key": ADMIN_API_KEY },
          },
        );
        if (!logsRes.ok) return null;
        const logs = await logsRes.json();
        if (!logs.summary) return null;

        // Calculate estimated cost from individual node runs
        let totalCost = 0;
        for (const run of logs.runs ?? []) {
          for (const tu of run.token_usage ?? []) {
            totalCost += estimateCost(
              tu.prompt_tokens,
              tu.completion_tokens,
              tu.model_name,
            );
          }
        }

        // Count retry rounds: count how many times the "editorial" node appears
        // (first occurrence is the initial run, each subsequent is a retry)
        const editorialRuns = (logs.runs ?? []).filter(
          (r: { node_name: string }) => r.node_name === "editorial",
        ).length;
        const retryCount = Math.max(0, editorialRuns - 1);

        return {
          total_duration_ms: logs.summary.total_duration_ms,
          estimated_cost_usd: totalCost,
          retry_count: retryCount,
        };
      } catch {
        return null;
      }
    }),
  );

  // Merge summaries into items
  const enriched = items.map(
    (item: Record<string, unknown>, i: number) => ({
      ...item,
      pipeline_summary: summaries[i],
    }),
  );

  return NextResponse.json({ items: enriched, total: data.total });
}
