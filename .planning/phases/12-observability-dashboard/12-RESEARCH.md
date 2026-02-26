# Phase 12: Observability Dashboard - Research

**Researched:** 2026-02-26
**Domain:** Admin UI visualization of pipeline execution logs, token/cost display, list page status indicators
**Confidence:** HIGH

## Summary

This phase builds the frontend visualization layer for the observability backend created in Phase 10. The backend already provides a complete API at `GET /api/contents/{id}/logs` returning per-node execution logs with timing, token usage, status, and IO data, plus an aggregated `PipelineRunSummary`. The admin UI (Next.js 15 + shadcn/ui + Tailwind CSS 4 + Radix UI) already has a tab-based detail page (`ContentTabs` with Magazine/JSON tabs) that needs a third "Pipeline" tab, and a list page (`ContentTable` using `@tanstack/react-table`) that needs pipeline status indicators.

The primary work is: (1) a BFF proxy route for logs API, (2) TypeScript types mirroring the `LogsResponse` schema, (3) a Pipeline tab with Gantt-style timeline + drill-down detail panels, (4) cost calculation utility using Gemini 2.5 Flash pricing, and (5) enhanced list table columns with step indicators and summary metrics.

**Primary recommendation:** Build everything with existing dependencies (Tailwind CSS, Radix UI, lucide-react, date-fns). The Gantt-style timeline uses pure CSS (flexbox/grid with percentage-width bars), no charting library needed. Cost calculation is a simple client-side utility with a pricing lookup table.

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Next.js | 15.5.12 | App Router, RSC for detail page, BFF proxy routes | Already the framework |
| Tailwind CSS | 4.x | All styling including timeline bars, status badges | Already configured |
| Radix UI (via radix-ui) | 1.4.3 | Tabs primitive (for Pipeline tab), Collapsible (for drill-down) | Already in use for tabs |
| shadcn/ui | 3.8.5 (dev CLI) | Badge, Card, Tabs, Skeleton UI components | Already the component system |
| @tanstack/react-table | 8.21.3 | Enhanced list table with new columns | Already in use for ContentTable |
| lucide-react | 0.575.0 | Icons for status, steps, expand/collapse | Already in use throughout |
| date-fns | 4.1.0 | Duration formatting, timestamp display | Already in use for `formatDate` |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| class-variance-authority | 0.7.1 | Variant-based styling for status colors, step indicators | Already in use for UI primitives |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| CSS-only Gantt bars | recharts/nivo/visx | Charting library is overkill for a simple horizontal bar layout; adds ~50-150KB bundle; the timeline has max 8 nodes, not dynamic data |
| Pure div timeline | `<canvas>` or SVG | Canvas/SVG give pixel-perfect control but are harder to style with Tailwind; divs with percentage widths work perfectly for 5-10 bars |
| Client-side cost calc | Backend cost field | CONTEXT decision: "모델별 동적 가격 반영" — calculating on frontend allows price updates without backend deploy; Phase 10 research also recommended this |

**Installation:** No new packages needed. Everything uses existing dependencies.

## Architecture Patterns

### Recommended Project Structure
```
admin/src/
├── app/
│   ├── api/contents/[id]/logs/route.ts    # NEW: BFF proxy for logs API
│   └── contents/[id]/page.tsx             # MODIFY: pass logs data to tabs
├── components/
│   ├── content-tabs.tsx                    # MODIFY: add Pipeline tab
│   ├── content-table.tsx                   # MODIFY: add pipeline status columns
│   ├── pipeline/
│   │   ├── pipeline-tab.tsx               # NEW: Pipeline tab container (summary + timeline)
│   │   ├── timeline-bar.tsx               # NEW: Single Gantt bar for one node
│   │   ├── node-detail-panel.tsx          # NEW: Expandable detail for clicked node
│   │   ├── cost-summary-card.tsx          # NEW: Total cost + token summary
│   │   └── cost-utils.ts                  # NEW: Pricing constants + calculation
│   ├── pipeline-status-indicator.tsx       # NEW: Step dots + badge for list page
│   └── content-status-badge.tsx            # MODIFY: add pipeline-aware statuses
├── lib/
│   └── types.ts                           # MODIFY: add log response types
```

### Pattern 1: BFF Proxy for Logs API
**What:** A Next.js API route that proxies to the FastAPI backend's `/api/contents/{id}/logs` endpoint, hiding the API key.
**When to use:** Same pattern as existing `admin/src/app/api/contents/[id]/route.ts`.
**Example:**
```typescript
// admin/src/app/api/contents/[id]/logs/route.ts
// Source: Existing BFF proxy pattern in admin/src/app/api/contents/[id]/route.ts
import { NextRequest, NextResponse } from "next/server";
import { API_BASE_URL, ADMIN_API_KEY } from "@/config";

export async function GET(
  request: NextRequest,
  { params }: { params: Promise<{ id: string }> },
) {
  const { id } = await params;
  const includeIo = request.nextUrl.searchParams.get("include_io") ?? "true";

  const res = await fetch(
    `${API_BASE_URL}/api/contents/${id}/logs?include_io=${includeIo}`,
    {
      cache: "no-store",
      headers: { "X-API-Key": ADMIN_API_KEY },
    },
  );
  const data = await res.json();
  return NextResponse.json(data, { status: res.status });
}
```

### Pattern 2: Server-Side Data Fetch in Detail Page
**What:** The detail page (RSC) fetches both content and logs data, passing logs to the Pipeline tab via ContentTabs props.
**When to use:** Page-level data loading for the Pipeline tab.
**Example:**
```typescript
// In admin/src/app/contents/[id]/page.tsx
// Fetch logs alongside content (parallel fetch)
const [content, logsData] = await Promise.all([
  apiGet<ContentItem>(`/api/contents/${id}`),
  apiGet<LogsResponse>(`/api/contents/${id}/logs?include_io=false`).catch(() => null),
]);

// Pass to ContentTabs
<ContentTabs
  blocks={blocks}
  designSpec={designSpec}
  layoutJson={content.layout_json}
  logs={logsData}                    // NEW prop
  contentId={content.id}             // for lazy-loading IO data
/>
```

### Pattern 3: CSS-Only Gantt Timeline Bars
**What:** Horizontal bars using flexbox with percentage-based widths relative to total pipeline duration.
**When to use:** The Gantt-style overview in the Pipeline tab.
**Example:**
```typescript
// Source: Pure CSS approach — no library needed
// Each bar width = (node_duration_ms / total_duration_ms) * 100%
function TimelineBar({ node, totalDurationMs }: Props) {
  const widthPercent = (node.duration_ms / totalDurationMs) * 100;
  const offsetPercent = (offsetMs / totalDurationMs) * 100;

  return (
    <div className="flex items-center gap-3 py-1">
      <span className="w-24 text-xs font-medium truncate">{node.node_name}</span>
      <div className="flex-1 relative h-6 bg-muted/30 rounded">
        <div
          className={cn(
            "absolute h-full rounded cursor-pointer transition-colors",
            node.status === "error" ? "bg-red-400 hover:bg-red-500"
              : "bg-blue-400 hover:bg-blue-500"
          )}
          style={{ left: `${offsetPercent}%`, width: `${Math.max(widthPercent, 1)}%` }}
          onClick={() => onSelect(node)}
        />
      </div>
      <span className="w-16 text-xs text-muted-foreground text-right">
        {formatDuration(node.duration_ms)}
      </span>
    </div>
  );
}
```

### Pattern 4: Expandable Node Detail (Click-to-Expand)
**What:** When a user clicks a Gantt bar, a detail panel expands below showing tokens, errors, and IO data.
**When to use:** Drill-down from the timeline overview.
**Example:**
```typescript
// Collapsible detail panel for a selected node
// Uses Radix Collapsible or simple state toggle
function NodeDetailPanel({ node, contentId }: Props) {
  const [ioData, setIoData] = useState<{ input: unknown; output: unknown } | null>(null);

  // Lazy-load IO data only when expanded
  async function loadIoData() {
    const data = await fetch(`/api/contents/${contentId}/logs?include_io=true`);
    // Extract matching node's IO from response
  }

  return (
    <div className="border rounded-lg p-4 bg-muted/20 space-y-3">
      {/* Token usage: "1,240 input + 890 output = 2,130 tokens" */}
      {/* Duration, model name, call count */}
      {/* Error details if status === "error" */}
      {/* IO data toggle with lazy loading */}
    </div>
  );
}
```

### Pattern 5: Cost Calculation Utility
**What:** Client-side utility with a pricing lookup table for token cost estimation.
**When to use:** Display cost in summary card and per-node detail.
**Example:**
```typescript
// Source: Gemini pricing page (ai.google.dev/pricing) — verified 2026-02-26
const PRICING: Record<string, { input: number; output: number }> = {
  "gemini-2.5-flash": { input: 0.30, output: 2.50 },  // per 1M tokens
  "gemini-2.5-flash-preview-image-generation": { input: 0.30, output: 30.00 },
};

export function estimateCost(
  promptTokens: number,
  completionTokens: number,
  modelName?: string | null,
): number {
  const key = modelName ?? "gemini-2.5-flash";
  const pricing = PRICING[key] ?? PRICING["gemini-2.5-flash"];
  return (promptTokens * pricing.input + completionTokens * pricing.output) / 1_000_000;
}

export function formatCost(usd: number): string {
  if (usd < 0.01) return `~$${(usd * 100).toFixed(2)}c`;
  return `~$${usd.toFixed(4)}`;
}
```

### Pattern 6: List Page Step Indicator
**What:** Combination of step dots and text badge showing pipeline progress inline in the table.
**When to use:** ContentTable new column for pipeline status.
**Example:**
```typescript
// Badge + step dots: "●●●○○ [큐레이션 중]"
const PIPELINE_STEPS_MAP: Record<string, { index: number; label: string }> = {
  curating:           { index: 0, label: "Curating" },
  sourcing:           { index: 1, label: "Sourcing" },
  drafting:           { index: 2, label: "Drafting" },
  reviewing:          { index: 3, label: "Reviewing" },
  awaiting_approval:  { index: 4, label: "Awaiting Approval" },
  published:          { index: 5, label: "Published" },
  failed:             { index: -1, label: "Failed" },
};

function PipelineStatusIndicator({ status }: { status: string }) {
  const step = PIPELINE_STEPS_MAP[status];
  if (!step) return null;

  const totalSteps = 5;
  return (
    <div className="flex items-center gap-2">
      <div className="flex gap-0.5">
        {Array.from({ length: totalSteps }, (_, i) => (
          <span key={i} className={cn(
            "inline-block h-2 w-2 rounded-full",
            step.index === -1 ? "bg-red-400"
              : i <= step.index ? "bg-blue-500" : "bg-muted-foreground/20"
          )} />
        ))}
      </div>
      <Badge variant="outline" className="text-xs">{step.label}</Badge>
    </div>
  );
}
```

### Anti-Patterns to Avoid
- **Fetching logs with include_io=true for the timeline overview:** IO data can be 50-200KB per node. Fetch without IO first, lazy-load per-node IO on expand. The API already supports `?include_io=false`.
- **Real-time polling on the Pipeline tab:** CONTEXT decision says "목록은 새로고침 시에만 상태 업데이트." Keep it simple — no WebSocket, no auto-refresh on the Pipeline tab.
- **Building a custom charting solution:** For 5-10 horizontal bars, CSS flexbox is more maintainable than any charting library. No dependency needed.
- **Putting cost calculation on the backend:** CONTEXT says "모델별 동적 가격 반영 (Phase 13 모델 라우팅 도입 대비)." Frontend calculation allows price updates without backend changes.
- **Modifying the Python backend:** Phase scope explicitly states "새로운 메트릭 수집이나 백엔드 변경은 범위 밖." All work is admin UI + BFF proxy.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Duration formatting (45230ms -> "45.2s") | Custom string concatenation | `date-fns` `formatDuration` + `intervalToDuration` or simple utility | Already in deps; edge cases like hours/minutes handled |
| Number formatting (1240 -> "1,240") | Manual regex/locale logic | `Intl.NumberFormat` | Built into every browser; handles locale-aware comma placement |
| Tab component | Custom tab state manager | Existing `Tabs`/`TabsList`/`TabsTrigger`/`TabsContent` from shadcn | Already used in ContentTabs and ContentTable |
| Collapsible panel | Custom height animation | Radix `Collapsible` (already bundled via `radix-ui@1.4.3`) | Handles accessibility, keyboard nav, animation |
| Table columns | Manual HTML table | Existing `@tanstack/react-table` setup in ContentTable | Column definitions, sorting, rendering already established |

**Key insight:** The admin UI already has every UI primitive needed. This phase is pure composition of existing components with new data, not new infrastructure.

## Common Pitfalls

### Pitfall 1: Log Data Missing for New Content
**What goes wrong:** Pipeline tab shows empty state for content that was created before Phase 10 was deployed, or for content whose JSONL file was deleted.
**Why it happens:** JSONL logs only exist for runs executed after Phase 10 instrumentation was added.
**How to avoid:** Show a clear empty state message like "No pipeline logs available for this content" with explanation. The API already returns `{ runs: [], summary: null }` for missing logs.
**Warning signs:** Empty Pipeline tab with no explanation; users think it's broken.

### Pitfall 2: Review Retry Loop Creates Duplicate Node Entries
**What goes wrong:** The timeline shows multiple `editorial` and `review` bars because the review loop re-executes these nodes.
**Why it happens:** When review fails, the graph routes back to `editorial -> enrich -> review`, creating additional log entries with the same node names.
**How to avoid:** This is expected behavior. Group repeated nodes by attempt/round. Detect retries by counting occurrences of the same node_name. Display as "editorial (attempt 1)", "editorial (attempt 2)" or visually separate retry rounds with dividers.
**Warning signs:** Timeline looks confusing with many bars of the same color for same node.

### Pitfall 3: Timeline Bar Width Too Small for Fast Nodes
**What goes wrong:** Nodes like `enrich` (pure data transform, <100ms) produce invisibly thin bars when the pipeline total is 45+ seconds.
**Why it happens:** Percentage-based width: 100ms / 45000ms = 0.2% width.
**How to avoid:** Set a minimum bar width (e.g., `Math.max(widthPercent, 1)%`) so every node is at least clickable. Show exact duration in the label regardless.
**Warning signs:** Missing bars in the timeline; users can't click on fast nodes.

### Pitfall 4: ContentTabs Becomes Heavy Client Component
**What goes wrong:** Adding logs data and the Pipeline tab makes ContentTabs a large client component with complex state.
**Why it happens:** ContentTabs is already "use client" for tab switching. Adding pipeline visualization with expand/collapse state increases complexity.
**How to avoid:** Keep the Pipeline tab as a separate client component (`PipelineTab`) imported into ContentTabs. This isolates state and allows code splitting. The timeline rendering and node selection state stay within PipelineTab.
**Warning signs:** ContentTabs growing beyond 200 lines; all pipeline state leaking into the tab container.

### Pitfall 5: Stale Pipeline Status on List Page
**What goes wrong:** List page shows outdated pipeline status because list items come from Supabase `contents` table which may not have the latest `pipeline_status`.
**Why it happens:** `pipeline_status` lives in LangGraph state (checkpoint), not in the Supabase `contents` table. The content list API returns `status` (pending/approved/rejected/published), not `pipeline_status`.
**How to avoid:** For the list page, use the content's `status` field (which IS in the DB) for the primary badge, and only show pipeline step progress from log data if available. Consider adding a lightweight log summary endpoint or including log metadata in the content list response. Alternative: just show the DB `status` with an enhanced badge, and leave detailed pipeline status to the detail page.
**Warning signs:** List page tries to fetch logs for every item, causing N+1 API calls.

### Pitfall 6: TypeScript Type Mismatch with Python API Response
**What goes wrong:** Frontend types don't match the actual API response shape.
**Why it happens:** Python datetime serialization produces ISO strings; field names in Python use snake_case; nullable fields may come as `null` vs `undefined`.
**How to avoid:** Mirror types exactly from `src/editorial_ai/api/schemas.py` (already verified in codebase analysis). The response models are: `LogsResponse` containing `runs: NodeRunLogResponse[]` and `summary: PipelineRunSummaryResponse | null`. All datetimes become ISO strings. All fields use snake_case.
**Warning signs:** Runtime errors from accessing undefined fields; TypeScript compile errors from wrong shapes.

## Code Examples

### Example 1: TypeScript Types for Log API Response
```typescript
// Source: Mirrors src/editorial_ai/api/schemas.py (lines 70-122)
export interface TokenUsageItem {
  prompt_tokens: number;
  completion_tokens: number;
  total_tokens: number;
  model_name: string | null;
}

export interface NodeRunLog {
  node_name: string;
  status: "success" | "error" | "skipped";
  started_at: string;   // ISO datetime
  ended_at: string;     // ISO datetime
  duration_ms: number;
  token_usage: TokenUsageItem[];
  total_prompt_tokens: number;
  total_completion_tokens: number;
  total_tokens: number;
  prompt_chars: number;
  error_type: string | null;
  error_message: string | null;
  input_state: Record<string, unknown> | null;
  output_state: Record<string, unknown> | null;
}

export interface PipelineRunSummary {
  thread_id: string;
  node_count: number;
  total_duration_ms: number;
  total_prompt_tokens: number;
  total_completion_tokens: number;
  total_tokens: number;
  status: "completed" | "failed" | "running";
  started_at: string | null;
  ended_at: string | null;
}

export interface LogsResponse {
  content_id: string;
  thread_id: string;
  runs: NodeRunLog[];
  summary: PipelineRunSummary | null;
}
```

### Example 2: Cost Summary Card
```typescript
// Renders at the top of Pipeline tab
function CostSummaryCard({ summary, runs }: { summary: PipelineRunSummary; runs: NodeRunLog[] }) {
  // Aggregate cost from all node token usages
  const totalCost = runs.reduce((acc, run) => {
    return acc + run.token_usage.reduce((nodeAcc, tu) => {
      return nodeAcc + estimateCost(tu.prompt_tokens, tu.completion_tokens, tu.model_name);
    }, 0);
  }, 0);

  return (
    <Card className="p-4">
      <div className="grid grid-cols-4 gap-4 text-sm">
        <div>
          <div className="text-muted-foreground">Total Duration</div>
          <div className="text-lg font-semibold">{formatDuration(summary.total_duration_ms)}</div>
        </div>
        <div>
          <div className="text-muted-foreground">Total Tokens</div>
          <div className="text-lg font-semibold">
            {new Intl.NumberFormat().format(summary.total_tokens)}
          </div>
          <div className="text-xs text-muted-foreground">
            {new Intl.NumberFormat().format(summary.total_prompt_tokens)} in +{" "}
            {new Intl.NumberFormat().format(summary.total_completion_tokens)} out
          </div>
        </div>
        <div>
          <div className="text-muted-foreground">Estimated Cost</div>
          <div className="text-lg font-semibold">{formatCost(totalCost)}</div>
        </div>
        <div>
          <div className="text-muted-foreground">Nodes</div>
          <div className="text-lg font-semibold">{summary.node_count}</div>
          <div className="text-xs text-muted-foreground">
            Status: <Badge variant={summary.status === "failed" ? "destructive" : "default"}>
              {summary.status}
            </Badge>
          </div>
        </div>
      </div>
    </Card>
  );
}
```

### Example 3: Duration Formatting Utility
```typescript
// Simple duration formatter — no library needed for this specific case
export function formatDuration(ms: number): string {
  if (ms < 1000) return `${Math.round(ms)}ms`;
  if (ms < 60_000) return `${(ms / 1000).toFixed(1)}s`;
  const minutes = Math.floor(ms / 60_000);
  const seconds = ((ms % 60_000) / 1000).toFixed(0);
  return `${minutes}m ${seconds}s`;
}
```

### Example 4: Review Retry Round Detection
```typescript
// Detect retry rounds by finding repeated node_name sequences
function groupByRound(runs: NodeRunLog[]): { round: number; nodes: NodeRunLog[] }[] {
  const rounds: { round: number; nodes: NodeRunLog[] }[] = [];
  let currentRound = 1;
  let currentNodes: NodeRunLog[] = [];

  for (const run of runs) {
    // A new round starts when we see "editorial" again after already seeing it
    if (run.node_name === "editorial" && currentNodes.some(n => n.node_name === "editorial")) {
      rounds.push({ round: currentRound, nodes: currentNodes });
      currentRound++;
      currentNodes = [run];
    } else {
      currentNodes.push(run);
    }
  }

  if (currentNodes.length > 0) {
    rounds.push({ round: currentRound, nodes: currentNodes });
  }

  return rounds;
}
```

## Discretion Recommendations

### Timeline Real-Time Update (During Execution)
**Recommendation:** Show completed data only (no polling on Pipeline tab). Rationale:
1. CONTEXT decision for list page: "목록은 새로고침 시에만 상태 업데이트 (실시간 폴링 없음)"
2. The Pipeline tab is a post-mortem analysis tool, not a real-time monitor
3. The NewContentModal already handles real-time progress display with its existing polling pattern
4. A manual "Refresh logs" button is sufficient for checking if a running pipeline has progressed

### Cost Summary Card Position
**Recommendation:** Inside the Pipeline tab, at the top before the timeline. Rationale:
1. Cost is contextual to the pipeline execution — not general content metadata
2. Placing it in the tab keeps the detail page header clean and focused on content metadata
3. The summary card provides at-a-glance metrics (duration, tokens, cost, node count) before the user drills into the timeline

### List Page Status Filtering
**Recommendation:** Reuse existing status tab filter (All/Pending/Approved/Rejected). No additional pipeline-phase filtering needed because:
1. The DB `status` field maps to content lifecycle stages that admins care about
2. Pipeline-phase filtering (curating/sourcing/drafting) would require N+1 log queries or a new backend field
3. The step indicator on each row provides visual pipeline progress without dedicated filters

### Error/Failure Visual Distinction
**Recommendation:** Use a multi-signal approach:
- **Timeline bar color:** Red/destructive for error nodes, blue/primary for success
- **Node label icon:** `AlertTriangle` icon (lucide) next to node name for errors
- **Detail panel:** Red-bordered card with error type, message, and first 5 lines of traceback (already stored by Phase 10 backend)
- **Summary badge:** "failed" badge in destructive variant on the summary card
- **Escalation:** For review escalation (max retries exceeded), show a distinct amber/warning banner: "Escalated: review failed after 3 attempts"

### Review Loop Retry Timeline Representation
**Recommendation:** Group by "round" with visual separators:
- Round 1: curation -> design_spec -> source -> editorial -> enrich -> review
- Round 2 (retry): editorial -> enrich -> review
- Each round gets a subtle horizontal divider with "Round N" label
- Bars within each round are sequential
- This makes it clear how many retry iterations occurred and what ran in each

### Escalation State Special Display
**Recommendation:** When the pipeline summary status is "failed" AND the last review node's error_message contains "Escalation:", show a prominent amber banner at the top of the Pipeline tab explaining that the review quality gate rejected the content after maximum retries. This is more informative than a generic "failed" state.

### Error Detail Expression
**Recommendation:** Show a compact summary by default with a "Show full error" toggle:
- Default view: error_type + first line of error_message (e.g., "ValidationError: 3 validation errors for MagazineLayout")
- Expanded view: full error_message + traceback (already limited to 5 lines by Phase 10 node_wrapper)
- Use monospace font (Geist Mono, already loaded) for traceback display

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Separate charting library for simple timelines | CSS-only with flexbox/grid | Always valid | No bundle size impact; simpler maintenance |
| Server Components for all data display | RSC for initial load + Client Component for interactivity | Next.js 13+ (2023) | Content detail page uses RSC for data fetch, ContentTabs is client for tab switching |

**Deprecated/outdated:**
- None relevant. The tech stack (Next.js 15, Tailwind 4, Radix UI) is current.

## Existing Codebase Integration Points

### Backend API (No Changes Required)
- `GET /api/contents/{content_id}/logs?include_io=true|false` — fully implemented in `src/editorial_ai/api/routes/logs.py`
- Returns `LogsResponse` with `runs: NodeRunLogResponse[]` and `summary: PipelineRunSummaryResponse | null`
- Registered at prefix `/api/contents` in `src/editorial_ai/api/app.py` line 58

### Frontend Entry Points
| File | Current State | What Changes |
|------|--------------|--------------|
| `admin/src/app/contents/[id]/page.tsx` | Fetches content, passes to ContentTabs | Also fetch logs, pass to ContentTabs |
| `admin/src/components/content-tabs.tsx` | 2 tabs: Magazine, JSON (36 lines) | Add 3rd tab: Pipeline |
| `admin/src/components/content-table.tsx` | 4 columns: Title, Status, Keyword, Created | Add Pipeline Status column |
| `admin/src/lib/types.ts` | ContentItem, MagazineLayout, etc. | Add LogsResponse types |
| `admin/src/lib/api.ts` | apiGet, apiPost utilities | No changes needed |
| `admin/src/components/content-status-badge.tsx` | 4 statuses: pending, approved, rejected, published | No changes needed (pipeline status uses separate indicator) |

### Pipeline Node Order (for timeline display)
From `src/editorial_ai/graph.py`:
```
curation -> design_spec -> source -> editorial -> enrich -> review -> admin_gate -> publish
```
With conditional edges:
- After `review`: -> `admin_gate` (pass) | -> `editorial` (retry) | -> END (max retries)
- After `admin_gate`: -> `publish` (approved) | -> `editorial` (revision) | -> END (rejected)

### Pipeline Status Values (from state.py)
```
"curating" | "sourcing" | "drafting" | "reviewing" | "awaiting_approval" | "published" | "failed"
```
Note: `design_spec` and `enrich` nodes don't set their own `pipeline_status` — status transitions are: curating -> sourcing -> drafting -> reviewing -> awaiting_approval -> published (or failed at any point).

### Gemini 2.5 Flash Pricing (verified 2026-02-26)
| Model | Input (per 1M tokens) | Output (per 1M tokens) |
|-------|-----------------------|------------------------|
| `gemini-2.5-flash` | $0.30 | $2.50 |
| `gemini-2.5-flash-preview-image-generation` | $0.30 | $30.00 (image output) |

## Open Questions

1. **List page pipeline_status availability**
   - What we know: The content list API (`GET /api/contents`) returns items from Supabase with `status` (pending/approved/rejected/published). Pipeline status lives in LangGraph checkpoint state, not the contents table. The content detail page CAN fetch logs, but list page would need N+1 calls.
   - What's unclear: Whether the step indicator on the list page should show pipeline phases or just the DB status.
   - Recommendation: For the list page, show the DB `status` with an enhanced badge (the existing ContentStatusBadge already handles this). The step dots can be static based on the DB status mapping (e.g., "pending" = all 5 filled = awaiting admin action; "approved" = all filled + green check). Detailed pipeline progress is only shown on the detail page Pipeline tab. This avoids N+1 API calls and keeps the list page fast.

2. **IO data lazy loading strategy**
   - What we know: The logs API supports `?include_io=false` to reduce payload. IO data per node can be 50-200KB.
   - What's unclear: Whether to fetch IO data per-node individually or re-fetch the entire logs response with `include_io=true` when any node is expanded.
   - Recommendation: Re-fetch the full logs response with `include_io=true` on first expand, then cache client-side. This is simpler than per-node fetching (which the API doesn't support), and a single extra request is acceptable for a drill-down action.

## Sources

### Primary (HIGH confidence)
- Codebase analysis: `src/editorial_ai/observability/models.py` (142 lines) — NodeRunLog, TokenUsage, PipelineRunSummary exact field names and types
- Codebase analysis: `src/editorial_ai/api/schemas.py` (122 lines) — LogsResponse, NodeRunLogResponse exact API response shape
- Codebase analysis: `src/editorial_ai/api/routes/logs.py` (99 lines) — Endpoint implementation, include_io parameter
- Codebase analysis: `admin/src/components/content-tabs.tsx` (36 lines) — Current tab structure to extend
- Codebase analysis: `admin/src/components/content-table.tsx` (217 lines) — Current table columns and @tanstack/react-table setup
- Codebase analysis: `admin/src/app/api/contents/[id]/route.ts` — BFF proxy pattern to replicate
- Codebase analysis: `src/editorial_ai/graph.py` — Node order, conditional edges, retry routing
- Codebase analysis: `src/editorial_ai/state.py` — pipeline_status literal values
- Codebase analysis: `admin/package.json` — Confirmed all UI dependencies available
- Gemini pricing page (ai.google.dev/pricing) — Verified 2026-02-26: Flash input $0.30/1M, output $2.50/1M

### Secondary (MEDIUM confidence)
- CSS flexbox for Gantt-style timelines — widely established pattern, no library needed for <10 bars
- Radix UI Collapsible primitive — part of `radix-ui@1.4.3` already installed

### Tertiary (LOW confidence)
- None. All findings verified against codebase or official sources.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all libraries already in the project, no new dependencies
- Architecture: HIGH — patterns mirror existing codebase (BFF proxy, RSC data fetch, client components for interactivity)
- Pitfalls: HIGH — identified from actual codebase analysis (review retries, IO data size, list page N+1, type mismatches)

**Research date:** 2026-02-26
**Valid until:** 2026-03-26 (stable domain, pricing may change)
