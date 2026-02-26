import { NextResponse } from "next/server";
import { API_BASE_URL, ADMIN_API_KEY, DEMO_MODE } from "@/config";
import { getDemoItemById } from "@/lib/demo-data";
import fs from "fs";
import path from "path";

const LOCAL_CONTENTS_DIR = path.join(process.cwd(), "..", "data", "contents");

/**
 * Recursively searches LOCAL_CONTENTS_DIR and all subdirectories for
 * a file named `<id>.json`. Returns the first match found, or null.
 */
function findLocalContentFile(dir: string, id: string): string | null {
  if (!fs.existsSync(dir)) return null;
  const directPath = path.join(dir, `${id}.json`);
  if (fs.existsSync(directPath)) return directPath;
  try {
    const entries = fs.readdirSync(dir, { withFileTypes: true });
    for (const entry of entries) {
      if (entry.isDirectory()) {
        const found = findLocalContentFile(path.join(dir, entry.name), id);
        if (found) return found;
      }
    }
  } catch {
    // ignore read errors
  }
  return null;
}

export async function GET(
  _request: Request,
  { params }: { params: Promise<{ id: string }> },
) {
  const { id } = await params;

  // Try local JSON file first (including subdirectories)
  const localPath = findLocalContentFile(LOCAL_CONTENTS_DIR, id);
  if (localPath) {
    try {
      const raw = fs.readFileSync(localPath, "utf-8");
      return NextResponse.json(JSON.parse(raw));
    } catch {
      // fall through
    }
  }

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
