import Link from "next/link";
import { notFound } from "next/navigation";

import { apiGet } from "@/lib/api";
import { formatDate } from "@/lib/utils";
import { ContentStatusBadge } from "@/components/content-status-badge";
import { BlockRenderer } from "@/components/block-renderer";
import { JsonPanel } from "@/components/json-panel";
import { ActionBar } from "./actions";
import type { ContentItem } from "@/lib/types";

export const dynamic = "force-dynamic";

interface ContentDetailPageProps {
  params: Promise<{ id: string }>;
}

export default async function ContentDetailPage({ params }: ContentDetailPageProps) {
  const { id } = await params;

  let content: ContentItem;
  try {
    content = await apiGet<ContentItem>(`/api/contents/${id}`);
  } catch (err) {
    if (err instanceof Error && err.message.includes("404")) {
      notFound();
    }
    return (
      <div className="flex min-h-[400px] items-center justify-center">
        <div className="rounded-lg border border-destructive/50 bg-destructive/5 p-6 text-center">
          <h2 className="text-lg font-semibold text-destructive">
            Failed to load content
          </h2>
          <p className="mt-2 text-sm text-muted-foreground">
            Please check that the API server is running and try again.
          </p>
          <Link
            href="/contents"
            className="mt-4 inline-block text-sm text-primary underline underline-offset-4"
          >
            Back to list
          </Link>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-8">
      {/* Action Bar */}
      <ActionBar contentId={content.id} initialStatus={content.status} />

      {/* Header */}
      <div>
        <div className="flex flex-wrap items-start gap-3">
          <h1 className="text-2xl font-bold tracking-tight">
            {content.title}
          </h1>
        </div>

        <div className="mt-2 flex flex-wrap gap-4 text-sm text-muted-foreground">
          <span>Keyword: {content.keyword}</span>
          <span>Created: {formatDate(content.created_at)}</span>
          <span>Updated: {formatDate(content.updated_at)}</span>
          {content.published_at && (
            <span>Published: {formatDate(content.published_at)}</span>
          )}
        </div>
      </div>

      {/* Metadata */}
      <div className="space-y-3">
        {content.review_summary && (
          <div className="rounded-lg border bg-muted/50 p-4">
            <h3 className="text-sm font-medium">Review Summary</h3>
            <p className="mt-1 text-sm text-muted-foreground">
              {content.review_summary}
            </p>
          </div>
        )}

        {content.rejection_reason && (
          <div className="rounded-lg border border-destructive/50 bg-destructive/5 p-4">
            <h3 className="text-sm font-medium text-destructive">
              Rejection Reason
            </h3>
            <p className="mt-1 text-sm text-destructive/80">
              {content.rejection_reason}
            </p>
          </div>
        )}

        {content.admin_feedback && (
          <div className="rounded-lg border bg-muted/50 p-4">
            <h3 className="text-sm font-medium">Admin Feedback</h3>
            <p className="mt-1 text-sm text-muted-foreground">
              {content.admin_feedback}
            </p>
          </div>
        )}
      </div>

      {/* Magazine Preview */}
      <div>
        <h2 className="mb-4 text-lg font-semibold">Magazine Preview</h2>
        <div className="rounded-lg border bg-white p-6">
          <BlockRenderer blocks={content.layout_json?.blocks ?? []} />
        </div>
      </div>

      {/* Raw JSON */}
      <JsonPanel data={content.layout_json} />
    </div>
  );
}
