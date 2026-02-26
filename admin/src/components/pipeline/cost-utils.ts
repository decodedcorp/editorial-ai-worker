// Gemini pricing (per 1M tokens) — verified 2026-02-26
// Source: ai.google.dev/pricing
const PRICING: Record<string, { input: number; output: number }> = {
  "gemini-2.5-flash": { input: 0.30, output: 2.50 },
  "gemini-2.5-flash-preview-image-generation": { input: 0.30, output: 30.0 },
};

const DEFAULT_MODEL = "gemini-2.5-flash";

/**
 * Estimate cost in USD from token counts.
 * Falls back to Gemini 2.5 Flash pricing for unknown models.
 */
export function estimateCost(
  promptTokens: number,
  completionTokens: number,
  modelName?: string | null,
): number {
  const key = modelName ?? DEFAULT_MODEL;
  const pricing = PRICING[key] ?? PRICING[DEFAULT_MODEL];
  return (promptTokens * pricing.input + completionTokens * pricing.output) / 1_000_000;
}

/**
 * Format USD cost for display.
 * Sub-cent values show as "~$0.00xx", otherwise show 2 decimal places.
 */
export function formatCost(usd: number): string {
  if (usd === 0) return "$0.00";
  if (usd < 0.01) return `~$${usd.toFixed(4)}`;
  return `~$${usd.toFixed(2)}`;
}

/**
 * Format milliseconds to human-readable duration.
 * Examples: "45ms", "3.2s", "1m 23s"
 */
export function formatDuration(ms: number): string {
  if (ms < 1000) return `${Math.round(ms)}ms`;
  if (ms < 60_000) return `${(ms / 1000).toFixed(1)}s`;
  const minutes = Math.floor(ms / 60_000);
  const seconds = Math.round((ms % 60_000) / 1000);
  return `${minutes}m ${seconds}s`;
}

/**
 * Format a number with locale-aware thousand separators.
 */
export function formatNumber(n: number): string {
  return new Intl.NumberFormat().format(n);
}
