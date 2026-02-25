import { NextRequest, NextResponse } from "next/server";
import { API_BASE_URL, ADMIN_API_KEY } from "@/config";

export async function GET(request: NextRequest) {
  const { searchParams } = request.nextUrl;
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
