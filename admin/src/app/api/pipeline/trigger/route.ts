import { NextRequest, NextResponse } from "next/server";
import { API_BASE_URL, ADMIN_API_KEY } from "@/config";

export async function POST(request: NextRequest) {
  const body = await request.json();
  const res = await fetch(`${API_BASE_URL}/api/pipeline/trigger`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      ...(ADMIN_API_KEY ? { "X-API-Key": ADMIN_API_KEY } : {}),
    },
    body: JSON.stringify(body),
    cache: "no-store",
  });
  const data = await res.json();
  return NextResponse.json(data, { status: res.status });
}
