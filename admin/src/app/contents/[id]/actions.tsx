"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { ArrowLeft, Loader2, Check, X } from "lucide-react";
import { Button } from "@/components/ui/button";
import { ContentStatusBadge } from "@/components/content-status-badge";
import { StickyActionBar } from "@/components/sticky-action-bar";
import { RejectForm } from "@/components/reject-form";

interface ActionBarProps {
  contentId: string;
  initialStatus: string;
}

export function ActionBar({ contentId, initialStatus }: ActionBarProps) {
  const router = useRouter();
  const [currentStatus, setCurrentStatus] = useState(initialStatus);
  const [showRejectForm, setShowRejectForm] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const isPending = currentStatus === "pending";

  async function handleApprove() {
    setIsLoading(true);
    setError(null);
    setCurrentStatus("approved");

    try {
      const res = await fetch(`/api/contents/${contentId}/approve`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({}),
      });

      if (!res.ok) {
        const data = await res.json().catch(() => null);
        throw new Error(data?.error ?? `Approve failed (${res.status})`);
      }

      router.refresh();
    } catch (err) {
      setCurrentStatus("pending");
      setError(err instanceof Error ? err.message : "Failed to approve content");
    } finally {
      setIsLoading(false);
    }
  }

  async function handleReject(reason: string) {
    setIsLoading(true);
    setError(null);
    setCurrentStatus("rejected");

    try {
      const res = await fetch(`/api/contents/${contentId}/reject`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ reason }),
      });

      if (!res.ok) {
        const data = await res.json().catch(() => null);
        throw new Error(data?.error ?? `Reject failed (${res.status})`);
      }

      setShowRejectForm(false);
      router.refresh();
    } catch (err) {
      setCurrentStatus("pending");
      setError(err instanceof Error ? err.message : "Failed to reject content");
    } finally {
      setIsLoading(false);
    }
  }

  return (
    <div>
      <StickyActionBar>
        <Button
          variant="ghost"
          size="sm"
          onClick={() => router.push("/contents")}
          className="gap-1"
        >
          <ArrowLeft className="size-4" />
          Back to list
        </Button>

        <div className="flex-1" />

        <ContentStatusBadge status={currentStatus} />

        {isPending ? (
          <div className="flex items-center gap-2">
            <Button
              size="sm"
              className="bg-green-600 hover:bg-green-700 text-white"
              onClick={handleApprove}
              disabled={isLoading}
            >
              {isLoading ? (
                <Loader2 className="size-4 animate-spin" />
              ) : (
                <Check className="size-4" />
              )}
              Approve
            </Button>
            <Button
              variant="outline"
              size="sm"
              className="border-destructive text-destructive hover:bg-destructive/10"
              onClick={() => setShowRejectForm(!showRejectForm)}
              disabled={isLoading}
            >
              <X className="size-4" />
              Reject
            </Button>
          </div>
        ) : (
          <span className="text-sm text-muted-foreground">
            This content has been {currentStatus}
          </span>
        )}
      </StickyActionBar>

      {error && (
        <div className="mx-6 mt-2 rounded-lg border border-destructive/50 bg-destructive/5 p-3 text-sm text-destructive">
          {error}
        </div>
      )}

      {showRejectForm && (
        <div className="mx-6 mt-2">
          <RejectForm
            onConfirm={handleReject}
            onCancel={() => setShowRejectForm(false)}
            isLoading={isLoading}
          />
        </div>
      )}
    </div>
  );
}
