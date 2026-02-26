"use client";

import { AlertTriangle } from "lucide-react";
import { formatDuration } from "./cost-utils";
import type { NodeRunLog } from "@/lib/types";

interface TimelineBarProps {
  node: NodeRunLog;
  totalDurationMs: number;
  pipelineStartMs: number;
  isSelected: boolean;
  onSelect: (node: NodeRunLog) => void;
}

export function TimelineBar({
  node,
  totalDurationMs,
  pipelineStartMs,
  isSelected,
  onSelect,
}: TimelineBarProps) {
  const nodeStartMs = new Date(node.started_at).getTime();
  const leftPct =
    totalDurationMs > 0
      ? ((nodeStartMs - pipelineStartMs) / totalDurationMs) * 100
      : 0;
  const widthPct =
    totalDurationMs > 0
      ? Math.max((node.duration_ms / totalDurationMs) * 100, 1)
      : 100;

  const isError = node.status === "error";

  const barColor = isError
    ? "bg-red-400 hover:bg-red-500"
    : "bg-blue-400 hover:bg-blue-500";

  const selectedRing = isSelected ? "ring-2 ring-blue-600" : "";

  return (
    <div className="flex items-center gap-2 py-1">
      {/* Node name */}
      <div className="w-28 shrink-0 truncate text-xs font-medium">
        <span className="flex items-center gap-1">
          {isError && (
            <AlertTriangle className="inline size-3 text-destructive" />
          )}
          {node.node_name}
        </span>
      </div>

      {/* Bar area */}
      <div className="relative h-7 flex-1 rounded bg-muted/30">
        <button
          type="button"
          className={`absolute h-full rounded cursor-pointer transition-colors ${barColor} ${selectedRing}`}
          style={{
            left: `${leftPct}%`,
            width: `${widthPct}%`,
          }}
          onClick={() => onSelect(node)}
          aria-label={`Select ${node.node_name} node`}
        >
          {widthPct > 8 && (
            <span className="px-2 text-xs font-medium text-white truncate">
              {formatDuration(node.duration_ms)}
            </span>
          )}
        </button>
      </div>

      {/* Duration label */}
      <div className="w-16 shrink-0 text-right text-xs text-muted-foreground">
        {formatDuration(node.duration_ms)}
      </div>
    </div>
  );
}
