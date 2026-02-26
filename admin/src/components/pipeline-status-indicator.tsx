import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";
import { Check, X } from "lucide-react";
import { formatDuration, formatCost } from "@/components/pipeline/cost-utils";
import type { PipelineSummaryFields } from "@/lib/types";

const TOTAL_STEPS = 5;

interface StatusConfig {
  filledSteps: number;
  label: string;
  dotColor: string;
  badgeVariant: "default" | "secondary" | "destructive" | "outline";
  badgeClassName: string;
  icon?: "check" | "x";
}

const STATUS_MAP: Record<string, StatusConfig> = {
  pending: {
    filledSteps: 5,
    label: "Awaiting Approval",
    dotColor: "bg-amber-400",
    badgeVariant: "secondary",
    badgeClassName: "bg-amber-100 text-amber-800 border-amber-200",
  },
  approved: {
    filledSteps: 5,
    label: "Approved",
    dotColor: "bg-green-500",
    badgeVariant: "default",
    badgeClassName: "bg-green-100 text-green-800 border-green-200",
    icon: "check",
  },
  published: {
    filledSteps: 5,
    label: "Published",
    dotColor: "bg-green-500",
    badgeVariant: "outline",
    badgeClassName: "",
    icon: "check",
  },
  rejected: {
    filledSteps: 5,
    label: "Rejected",
    dotColor: "bg-red-400",
    badgeVariant: "destructive",
    badgeClassName: "",
    icon: "x",
  },
};

interface PipelineStatusIndicatorProps {
  status: string;
  pipelineSummary?: PipelineSummaryFields | null;
}

export function PipelineStatusIndicator({
  status,
  pipelineSummary,
}: PipelineStatusIndicatorProps) {
  const config = STATUS_MAP[status];
  if (!config) return null;

  return (
    <div className="flex flex-col gap-0.5">
      {/* Row 1: Step dots + badge */}
      <div className="flex items-center gap-2">
        <div className="flex gap-0.5">
          {Array.from({ length: TOTAL_STEPS }, (_, i) => (
            <span
              key={i}
              className={cn(
                "inline-block h-1.5 w-1.5 rounded-full",
                i < config.filledSteps
                  ? config.dotColor
                  : "bg-muted-foreground/20",
              )}
            />
          ))}
        </div>
        <Badge
          variant={config.badgeVariant}
          className={cn("text-[10px] px-1.5 py-0", config.badgeClassName)}
        >
          {config.icon === "check" && <Check className="mr-0.5 size-2.5" />}
          {config.icon === "x" && <X className="mr-0.5 size-2.5" />}
          {config.label}
        </Badge>
      </div>
      {/* Row 2: Summary metrics (duration, cost, retries) */}
      {pipelineSummary && (
        <div className="flex items-center gap-2 text-[10px] text-muted-foreground">
          {pipelineSummary.total_duration_ms != null && (
            <span>{formatDuration(pipelineSummary.total_duration_ms)}</span>
          )}
          {pipelineSummary.estimated_cost_usd != null && (
            <span>{formatCost(pipelineSummary.estimated_cost_usd)}</span>
          )}
          {pipelineSummary.retry_count > 0 && (
            <span className="text-amber-600">
              {pipelineSummary.retry_count}{" "}
              {pipelineSummary.retry_count === 1 ? "retry" : "retries"}
            </span>
          )}
        </div>
      )}
    </div>
  );
}
