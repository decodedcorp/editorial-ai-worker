import { NextRequest, NextResponse } from "next/server";
import { API_BASE_URL, ADMIN_API_KEY } from "@/config";

export async function GET(request: NextRequest) {
  const { searchParams } = new URL(request.url);
  const q = searchParams.get("q") || "";
  const type = searchParams.get("type") || "all";
  const limit = searchParams.get("limit") || "10";

  const res = await fetch(
    `${API_BASE_URL}/api/sources/search?q=${encodeURIComponent(q)}&type=${type}&limit=${limit}`,
    {
      headers: {
        ...(ADMIN_API_KEY ? { "X-API-Key": ADMIN_API_KEY } : {}),
      },
      cache: "no-store",
    }
  );
  const data = await res.json();
  return NextResponse.json(data, { status: res.status });
}
