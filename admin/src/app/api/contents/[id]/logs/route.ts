import { NextRequest, NextResponse } from "next/server";
import { API_BASE_URL, ADMIN_API_KEY, DEMO_MODE } from "@/config";
import fs from "fs";
import path from "path";
import readline from "readline";

const LOCAL_CONTENTS_DIR = path.join(process.cwd(), "..", "data", "contents");
const LOCAL_LOGS_DIR = path.join(process.cwd(), "..", "data", "logs");

interface TokenUsage {
  prompt_tokens: number;
  completion_tokens: number;
  total_tokens: number;
  model_name: string | null;
}

interface NodeRunLog {
  thread_id: string;
  node_name: string;
  status: string;
  started_at: string;
  ended_at: string;
  duration_ms: number;
  token_usage: TokenUsage[];
  total_prompt_tokens: number;
  total_completion_tokens: number;
  total_tokens: number;
  prompt_chars: number;
  error_type: string | null;
  error_message: string | null;
  input_state: unknown;
  output_state: unknown;
}

/**
 * Read logs from local JSONL file for a given content.
 * Mirrors the Python /api/contents/{id}/logs endpoint logic.
 */
async function readLocalLogs(
  contentId: string,
  includeIo: boolean,
): Promise<{
  content_id: string;
  thread_id: string;
  runs: Partial<NodeRunLog>[];
  summary: Record<string, unknown> | null;
} | null> {
  // 1. Resolve content_id -> thread_id
  const contentPath = path.join(LOCAL_CONTENTS_DIR, `${contentId}.json`);
  if (!fs.existsSync(contentPath)) return null;

  let content: Record<string, unknown>;
  try {
    content = JSON.parse(fs.readFileSync(contentPath, "utf-8"));
  } catch {
    return null;
  }

  const threadId = content.thread_id as string;
  if (!threadId) return null;

  // 2. Read JSONL log file
  const logPath = path.join(LOCAL_LOGS_DIR, `${threadId}.jsonl`);
  if (!fs.existsSync(logPath)) {
    return {
      content_id: contentId,
      thread_id: threadId,
      runs: [],
      summary: null,
    };
  }

  const logs: NodeRunLog[] = [];
  const fileStream = fs.createReadStream(logPath, { encoding: "utf-8" });
  const rl = readline.createInterface({ input: fileStream, crlfDelay: Infinity });

  for await (const line of rl) {
    const trimmed = line.trim();
    if (!trimmed) continue;
    try {
      logs.push(JSON.parse(trimmed) as NodeRunLog);
    } catch {
      // skip malformed lines
    }
  }

  // 3. Sort chronologically
  logs.sort(
    (a, b) =>
      new Date(a.started_at).getTime() - new Date(b.started_at).getTime(),
  );

  // 4. Build runs (optionally strip IO)
  const runs = logs.map((log) => {
    const run: Partial<NodeRunLog> = {
      node_name: log.node_name,
      status: log.status,
      started_at: log.started_at,
      ended_at: log.ended_at,
      duration_ms: log.duration_ms,
      token_usage: log.token_usage ?? [],
      total_prompt_tokens: log.total_prompt_tokens ?? 0,
      total_completion_tokens: log.total_completion_tokens ?? 0,
      total_tokens: log.total_tokens ?? 0,
      prompt_chars: log.prompt_chars ?? 0,
      error_type: log.error_type ?? null,
      error_message: log.error_message ?? null,
    };
    if (includeIo) {
      run.input_state = log.input_state ?? null;
      run.output_state = log.output_state ?? null;
    } else {
      run.input_state = null;
      run.output_state = null;
    }
    return run;
  });

  // 5. Build summary
  let summary: Record<string, unknown> | null = null;
  if (logs.length > 0) {
    const totalDurationMs = logs.reduce(
      (sum, l) => sum + (l.duration_ms ?? 0),
      0,
    );
    const totalPromptTokens = logs.reduce(
      (sum, l) => sum + (l.total_prompt_tokens ?? 0),
      0,
    );
    const totalCompletionTokens = logs.reduce(
      (sum, l) => sum + (l.total_completion_tokens ?? 0),
      0,
    );
    const hasError = logs.some((l) => l.status === "error");
    const startedAt = logs[0].started_at;
    const endedAt = logs[logs.length - 1].ended_at;

    summary = {
      thread_id: threadId,
      node_count: logs.length,
      total_duration_ms: totalDurationMs,
      total_prompt_tokens: totalPromptTokens,
      total_completion_tokens: totalCompletionTokens,
      total_tokens: totalPromptTokens + totalCompletionTokens,
      status: hasError ? "failed" : "completed",
      started_at: startedAt,
      ended_at: endedAt,
    };
  }

  return {
    content_id: contentId,
    thread_id: threadId,
    runs,
    summary,
  };
}

export async function GET(
  request: NextRequest,
  { params }: { params: Promise<{ id: string }> },
) {
  const { id } = await params;

  if (DEMO_MODE) {
    return NextResponse.json({
      content_id: id,
      thread_id: "demo",
      runs: [],
      summary: null,
    });
  }

  // Try local JSONL files first (works without Python API server)
  const localLogs = await readLocalLogs(
    id,
    request.nextUrl.searchParams.get("include_io") !== "false",
  );
  if (localLogs && localLogs.runs.length > 0) {
    return NextResponse.json(localLogs);
  }

  // Fall through to Python API
  const includeIo = request.nextUrl.searchParams.get("include_io") ?? "true";
  try {
    const res = await fetch(
      `${API_BASE_URL}/api/contents/${id}/logs?include_io=${includeIo}`,
      {
        cache: "no-store",
        headers: { "X-API-Key": ADMIN_API_KEY },
      },
    );

    const data = await res.json();
    return NextResponse.json(data, { status: res.status });
  } catch {
    // Python API not available — return local result (possibly empty)
    if (localLogs) {
      return NextResponse.json(localLogs);
    }
    return NextResponse.json(
      {
        content_id: id,
        thread_id: "unknown",
        runs: [],
        summary: null,
      },
      { status: 200 },
    );
  }
}
