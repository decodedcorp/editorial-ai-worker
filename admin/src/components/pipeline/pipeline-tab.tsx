"use client";

import { useState, useCallback } from "react";
import type { LogsResponse, NodeRunLog } from "@/lib/types";
import { CostSummaryCard } from "./cost-summary-card";
import { TimelineBar } from "./timeline-bar";
import { NodeDetailPanel } from "./node-detail-panel";

interface PipelineTabProps {
  logs: LogsResponse | null;
  contentId: string;
}

interface Round {
  round: number;
  nodes: NodeRunLog[];
}

/** Group runs into retry rounds. A new round starts when a node_name repeats. */
function groupByRounds(runs: NodeRunLog[]): Round[] {
  const rounds: Round[] = [];
  let currentRound: NodeRunLog[] = [];
  let seenNames = new Set<string>();

  for (const run of runs) {
    if (seenNames.has(run.node_name)) {
      // Start a new round
      rounds.push({ round: rounds.length + 1, nodes: currentRound });
      currentRound = [];
      seenNames = new Set<string>();
    }
    seenNames.add(run.node_name);
    currentRound.push(run);
  }

  if (currentRound.length > 0) {
    rounds.push({ round: rounds.length + 1, nodes: currentRound });
  }

  return rounds;
}

function getRoundTiming(nodes: NodeRunLog[]) {
  const starts = nodes.map((n) => new Date(n.started_at).getTime());
  const ends = nodes.map((n) => new Date(n.ended_at).getTime());
  const pipelineStartMs = Math.min(...starts);
  const pipelineEndMs = Math.max(...ends);
  const totalDurationMs = pipelineEndMs - pipelineStartMs;
  return { pipelineStartMs, totalDurationMs };
}

export function PipelineTab({ logs, contentId }: PipelineTabProps) {
  const [selectedNode, setSelectedNode] = useState<NodeRunLog | null>(null);
  const [fullLogs, setFullLogs] = useState<LogsResponse | null>(null);
  const [ioLoading, setIoLoading] = useState(false);

  const loadIoData = useCallback(async () => {
    if (fullLogs || ioLoading) return;
    setIoLoading(true);
    try {
      const res = await fetch(
        `/api/contents/${contentId}/logs?include_io=true`,
      );
      if (res.ok) {
        const data = await res.json();
        setFullLogs(data);
      }
    } finally {
      setIoLoading(false);
    }
  }, [contentId, fullLogs, ioLoading]);

  // Empty state
  if (!logs || logs.runs.length === 0) {
    return (
      <div className="flex min-h-[200px] flex-col items-center justify-center text-center">
        <p className="text-sm font-medium text-muted-foreground">
          No pipeline logs available for this content.
        </p>
        <p className="mt-1 text-xs text-muted-foreground/70">
          Logs are recorded when the pipeline runs.
        </p>
      </div>
    );
  }

  const rounds = groupByRounds(logs.runs);
  const hasMultipleRounds = rounds.length > 1;

  // Check for escalation
  const isEscalated =
    logs.summary?.status === "failed" &&
    (() => {
      const reviewRuns = logs.runs.filter((r) => r.node_name === "review");
      const lastReview = reviewRuns[reviewRuns.length - 1];
      return lastReview?.error_message
        ?.toLowerCase()
        .includes("escalat");
    })();

  // Find the matching node from fullLogs for IO data
  const detailNode = selectedNode
    ? (fullLogs?.runs.find(
        (r) =>
          r.node_name === selectedNode.node_name &&
          r.started_at === selectedNode.started_at,
      ) ?? selectedNode)
    : null;

  return (
    <div className="space-y-4">
      {/* Cost summary */}
      {logs.summary && (
        <CostSummaryCard summary={logs.summary} runs={logs.runs} />
      )}

      {/* Escalation banner */}
      {isEscalated && (
        <div className="rounded-md border border-amber-300 bg-amber-50 px-4 py-3 text-sm text-amber-800 dark:border-amber-700 dark:bg-amber-950/30 dark:text-amber-300">
          Review escalated: quality gate rejected after maximum retry attempts.
        </div>
      )}

      {/* Timeline per round */}
      {rounds.map((round) => {
        const { pipelineStartMs, totalDurationMs } = getRoundTiming(
          round.nodes,
        );

        return (
          <div key={round.round}>
            {hasMultipleRounds && (
              <div className="mb-2 flex items-center gap-2">
                <div className="h-px flex-1 bg-border" />
                <span className="text-xs font-medium text-muted-foreground">
                  Round {round.round}
                </span>
                <div className="h-px flex-1 bg-border" />
              </div>
            )}

            <div className="space-y-0.5">
              {round.nodes.map((node) => (
                <TimelineBar
                  key={`${node.node_name}-${node.started_at}`}
                  node={node}
                  totalDurationMs={totalDurationMs}
                  pipelineStartMs={pipelineStartMs}
                  isSelected={
                    selectedNode?.node_name === node.node_name &&
                    selectedNode?.started_at === node.started_at
                  }
                  onSelect={(n) =>
                    setSelectedNode(
                      selectedNode?.node_name === n.node_name &&
                        selectedNode?.started_at === n.started_at
                        ? null
                        : n,
                    )
                  }
                />
              ))}
            </div>
          </div>
        );
      })}

      {/* Detail panel */}
      {selectedNode && detailNode && (
        <NodeDetailPanel
          node={detailNode}
          contentId={contentId}
          onLoadIo={loadIoData}
          ioLoaded={!!fullLogs}
        />
      )}
    </div>
  );
}
