import { NextRequest, NextResponse } from "next/server";
import { API_BASE_URL, ADMIN_API_KEY, DEMO_MODE } from "@/config";

export async function GET(
  request: NextRequest,
  { params }: { params: Promise<{ id: string }> },
) {
  const { id } = await params;

  if (DEMO_MODE) {
    // Return empty logs in demo mode
    return NextResponse.json({
      content_id: id,
      thread_id: "demo",
      runs: [],
      summary: null,
    });
  }

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
