import { NextRequest, NextResponse } from "next/server";
import { API_BASE_URL, ADMIN_API_KEY, DEMO_MODE } from "@/config";
import { getDemoItems } from "@/lib/demo-data";

export async function GET(request: NextRequest) {
  const { searchParams } = request.nextUrl;

  if (DEMO_MODE) {
    const status = searchParams.get("status") || undefined;
    const limit = parseInt(searchParams.get("limit") || "20", 10);
    const offset = parseInt(searchParams.get("offset") || "0", 10);
    const items = getDemoItems(status);
    const paged = items.slice(offset, offset + limit);
    return NextResponse.json({ items: paged, total: items.length });
  }

  const url = new URL("/api/contents", API_BASE_URL);

  // Forward supported query params
  for (const key of ["status", "limit", "offset"]) {
    const value = searchParams.get(key);
    if (value) {
      url.searchParams.set(key, value);
    }
  }

  const res = await fetch(url.toString(), {
    cache: "no-store",
    headers: {
      "X-API-Key": ADMIN_API_KEY,
    },
  });

  const data = await res.json();
  return NextResponse.json(data, { status: res.status });
}
