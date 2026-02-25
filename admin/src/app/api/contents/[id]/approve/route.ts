import { NextResponse } from "next/server";
import { API_BASE_URL, ADMIN_API_KEY, DEMO_MODE } from "@/config";
import { approveDemoItem } from "@/lib/demo-data";

export async function POST(
  request: Request,
  { params }: { params: Promise<{ id: string }> },
) {
  const { id } = await params;

  if (DEMO_MODE) {
    const item = approveDemoItem(id);
    if (!item) {
      return NextResponse.json({ detail: "Not found" }, { status: 404 });
    }
    return NextResponse.json(item);
  }

  const body = await request.json();

  const res = await fetch(`${API_BASE_URL}/api/contents/${id}/approve`, {
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
