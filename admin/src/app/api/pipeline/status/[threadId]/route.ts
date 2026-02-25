import { NextRequest, NextResponse } from "next/server";
import { API_BASE_URL, ADMIN_API_KEY } from "@/config";

export async function GET(
  _request: NextRequest,
  { params }: { params: Promise<{ threadId: string }> }
) {
  const { threadId } = await params;
  const res = await fetch(`${API_BASE_URL}/api/pipeline/status/${threadId}`, {
    headers: {
      ...(ADMIN_API_KEY ? { "X-API-Key": ADMIN_API_KEY } : {}),
    },
    cache: "no-store",
  });
  const data = await res.json();
  return NextResponse.json(data, { status: res.status });
}
