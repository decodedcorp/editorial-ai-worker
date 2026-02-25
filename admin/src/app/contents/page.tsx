import Link from "next/link";
import { ContentTable } from "@/components/content-table";
import { NewContentModal } from "@/components/new-content-modal";
import { apiGet } from "@/lib/api";
import type { ContentListResponse } from "@/lib/types";

export const dynamic = "force-dynamic";

interface ContentsPageProps {
  searchParams: Promise<{ status?: string; page?: string }>;
}

export default async function ContentsPage({ searchParams }: ContentsPageProps) {
  const params = await searchParams;
  const status = params.status;
  const page = Math.max(1, Number(params.page) || 1);
  const limit = 20;
  const offset = (page - 1) * limit;

  const queryParams: Record<string, string> = {
    limit: String(limit),
    offset: String(offset),
  };
  if (status) {
    queryParams.status = status;
  }

  try {
    const data = await apiGet<ContentListResponse>("/api/contents", queryParams);

    return (
      <div className="space-y-6">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold tracking-tight">Contents</h1>
            <p className="text-muted-foreground">
              Browse and manage editorial content
            </p>
          </div>
          <NewContentModal />
        </div>
        <ContentTable
          items={data.items}
          total={data.total}
          page={page}
          limit={limit}
          currentStatus={status}
        />
      </div>
    );
  } catch {
    return (
      <div className="flex min-h-[400px] items-center justify-center">
        <div className="rounded-lg border border-destructive/50 bg-destructive/5 p-6 text-center">
          <h2 className="text-lg font-semibold text-destructive">
            Failed to load contents
          </h2>
          <p className="mt-2 text-sm text-muted-foreground">
            Please check that the API server is running and try again.
          </p>
          <Link
            href="/contents"
            className="mt-4 inline-block text-sm text-primary underline underline-offset-4"
          >
            Retry
          </Link>
        </div>
      </div>
    );
  }
}
