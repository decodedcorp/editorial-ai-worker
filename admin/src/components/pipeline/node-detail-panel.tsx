"use client";

import { useState } from "react";
import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import {
  estimateCost,
  formatCost,
  formatDuration,
  formatNumber,
} from "./cost-utils";
import type { NodeRunLog } from "@/lib/types";

interface NodeDetailPanelProps {
  node: NodeRunLog;
  contentId: string;
  onLoadIo: () => Promise<void>;
  ioLoaded: boolean;
}

export function NodeDetailPanel({
  node,
  contentId: _contentId,
  onLoadIo,
  ioLoaded,
}: NodeDetailPanelProps) {
  const [errorExpanded, setErrorExpanded] = useState(false);
  const [ioExpanded, setIoExpanded] = useState(false);
  const [ioLoading, setIoLoading] = useState(false);

  const statusVariant =
    node.status === "error"
      ? "destructive"
      : node.status === "success"
        ? "default"
        : "secondary";

  const handleLoadIo = async () => {
    setIoLoading(true);
    try {
      await onLoadIo();
    } finally {
      setIoLoading(false);
    }
  };

  return (
    <Card className="mt-3 py-4">
      <div className="space-y-4 px-6">
        {/* Header */}
        <div className="flex flex-wrap items-center gap-2">
          <h3 className="text-sm font-bold">{node.node_name}</h3>
          <Badge variant={statusVariant}>{node.status}</Badge>
          <span className="text-xs text-muted-foreground">
            {formatDuration(node.duration_ms)}
          </span>
          <Badge variant="secondary">
            LLM Calls: {node.token_usage.length}
          </Badge>
        </div>

        {/* Token usage breakdown */}
        {node.token_usage.length > 0 && (
          <div className="space-y-1">
            {node.token_usage.map((tu, i) => {
              const cost = estimateCost(
                tu.prompt_tokens,
                tu.completion_tokens,
                tu.model_name,
              );
              return (
                <div
                  key={i}
                  className="flex flex-wrap items-center gap-x-3 text-xs text-muted-foreground"
                >
                  <span>
                    {formatNumber(tu.prompt_tokens)} input +{" "}
                    {formatNumber(tu.completion_tokens)} output ={" "}
                    {formatNumber(tu.total_tokens)} tokens
                  </span>
                  {tu.model_name && (
                    <span className="text-muted-foreground/70">
                      {tu.model_name}
                    </span>
                  )}
                  <span>{formatCost(cost)}</span>
                </div>
              );
            })}
          </div>
        )}

        {/* Node totals */}
        <div className="text-xs font-medium">
          Total: {formatNumber(node.total_prompt_tokens)} in +{" "}
          {formatNumber(node.total_completion_tokens)} out ={" "}
          {formatNumber(node.total_tokens)} tokens
        </div>

        {/* Error section */}
        {node.error_type && (
          <div className="rounded-md border border-red-300 bg-red-50 p-3 dark:border-red-800 dark:bg-red-950/30">
            <div className="text-xs font-medium text-red-700 dark:text-red-400">
              {node.error_type}:{" "}
              {errorExpanded
                ? ""
                : node.error_message?.split("\n")[0] ?? ""}
            </div>
            {node.error_message && (
              <>
                <button
                  type="button"
                  className="mt-1 text-xs underline text-red-600 dark:text-red-400"
                  onClick={() => setErrorExpanded(!errorExpanded)}
                >
                  {errorExpanded ? "Hide full error" : "Show full error"}
                </button>
                {errorExpanded && (
                  <pre className="mt-2 max-h-60 overflow-auto whitespace-pre-wrap rounded bg-red-100 p-2 font-mono text-xs text-red-800 dark:bg-red-950 dark:text-red-200">
                    {node.error_message}
                  </pre>
                )}
              </>
            )}
          </div>
        )}

        {/* IO data section */}
        <div>
          {node.input_state || node.output_state ? (
            <>
              <button
                type="button"
                className="text-xs underline text-muted-foreground"
                onClick={() => setIoExpanded(!ioExpanded)}
              >
                {ioExpanded ? "Hide IO data" : "Show IO data"}
              </button>
              {ioExpanded && (
                <div className="mt-2 space-y-2">
                  {node.input_state && (
                    <div>
                      <p className="mb-1 text-xs font-medium text-muted-foreground">
                        Input State
                      </p>
                      <pre className="max-h-60 overflow-auto rounded bg-slate-950 p-3 font-mono text-xs text-slate-100">
                        {JSON.stringify(node.input_state, null, 2)}
                      </pre>
                    </div>
                  )}
                  {node.output_state && (
                    <div>
                      <p className="mb-1 text-xs font-medium text-muted-foreground">
                        Output State
                      </p>
                      <pre className="max-h-60 overflow-auto rounded bg-slate-950 p-3 font-mono text-xs text-slate-100">
                        {JSON.stringify(node.output_state, null, 2)}
                      </pre>
                    </div>
                  )}
                </div>
              )}
            </>
          ) : (
            <button
              type="button"
              className="text-xs underline text-muted-foreground disabled:opacity-50"
              disabled={ioLoading || ioLoaded}
              onClick={handleLoadIo}
            >
              {ioLoading
                ? "Loading IO data..."
                : ioLoaded
                  ? "No IO data available"
                  : "Load IO data"}
            </button>
          )}
        </div>
      </div>
    </Card>
  );
}
