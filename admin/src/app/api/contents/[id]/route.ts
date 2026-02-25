import { NextResponse } from "next/server";
import { API_BASE_URL, ADMIN_API_KEY, DEMO_MODE } from "@/config";
import { getDemoItemById } from "@/lib/demo-data";

export async function GET(
  _request: Request,
  { params }: { params: Promise<{ id: string }> },
) {
  const { id } = await params;

  if (DEMO_MODE) {
    const item = getDemoItemById(id);
    if (!item) {
      return NextResponse.json({ detail: "Not found" }, { status: 404 });
    }
    return NextResponse.json(item);
  }

  const res = await fetch(`${API_BASE_URL}/api/contents/${id}`, {
    cache: "no-store",
    headers: {
      "X-API-Key": ADMIN_API_KEY,
    },
  });

  const data = await res.json();
  return NextResponse.json(data, { status: res.status });
}
