"use client";

import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import {
  estimateCost,
  formatCost,
  formatDuration,
  formatNumber,
} from "./cost-utils";
import type { PipelineRunSummary, NodeRunLog } from "@/lib/types";

interface CostSummaryCardProps {
  summary: PipelineRunSummary;
  runs: NodeRunLog[];
}

export function CostSummaryCard({ summary, runs }: CostSummaryCardProps) {
  // Calculate total cost from all token usage entries (per-model accuracy)
  const totalCost = runs.reduce((acc, run) => {
    return (
      acc +
      run.token_usage.reduce(
        (sum, tu) =>
          sum + estimateCost(tu.prompt_tokens, tu.completion_tokens, tu.model_name),
        0,
      )
    );
  }, 0);

  const statusVariant =
    summary.status === "failed"
      ? "destructive"
      : summary.status === "completed"
        ? "default"
        : "secondary";

  return (
    <Card className="py-4">
      <div className="grid grid-cols-2 gap-4 px-6 md:grid-cols-4">
        {/* Total Duration */}
        <div>
          <p className="text-xs font-medium text-muted-foreground">
            Total Duration
          </p>
          <p className="mt-1 text-lg font-semibold">
            {formatDuration(summary.total_duration_ms)}
          </p>
        </div>

        {/* Total Tokens */}
        <div>
          <p className="text-xs font-medium text-muted-foreground">
            Total Tokens
          </p>
          <p className="mt-1 text-lg font-semibold">
            {formatNumber(summary.total_tokens)}
          </p>
          <p className="text-xs text-muted-foreground">
            {formatNumber(summary.total_prompt_tokens)} in +{" "}
            {formatNumber(summary.total_completion_tokens)} out
          </p>
        </div>

        {/* Estimated Cost */}
        <div>
          <p className="text-xs font-medium text-muted-foreground">
            Estimated Cost
          </p>
          <p className="mt-1 text-lg font-semibold">{formatCost(totalCost)}</p>
        </div>

        {/* Nodes */}
        <div>
          <p className="text-xs font-medium text-muted-foreground">Nodes</p>
          <div className="mt-1 flex items-center gap-2">
            <span className="text-lg font-semibold">{summary.node_count}</span>
            <Badge variant={statusVariant}>{summary.status}</Badge>
          </div>
        </div>
      </div>
    </Card>
  );
}
