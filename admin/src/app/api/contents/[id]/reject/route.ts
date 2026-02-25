import { NextResponse } from "next/server";
import { API_BASE_URL, ADMIN_API_KEY, DEMO_MODE } from "@/config";
import { rejectDemoItem } from "@/lib/demo-data";

export async function POST(
  request: Request,
  { params }: { params: Promise<{ id: string }> },
) {
  const { id } = await params;
  const body = await request.json();

  if (DEMO_MODE) {
    const item = rejectDemoItem(id, body.reason || "");
    if (!item) {
      return NextResponse.json({ detail: "Not found" }, { status: 404 });
    }
    return NextResponse.json(item);
  }

  const res = await fetch(`${API_BASE_URL}/api/contents/${id}/reject`, {
    method: "POST",
    cache: "no-store",
    headers: {
      "Content-Type": "application/json",
      "X-API-Key": ADMIN_API_KEY,
    },
    body: JSON.stringify(body),
  });

  const data = await res.json();
  return NextResponse.json(data, { status: res.status });
}
