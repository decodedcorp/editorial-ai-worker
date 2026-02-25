"use client";

import { useState } from "react";
import { Textarea } from "@/components/ui/textarea";
import { Button } from "@/components/ui/button";

interface RejectFormProps {
  onConfirm: (reason: string) => void;
  onCancel: () => void;
  isLoading: boolean;
}

export function RejectForm({ onConfirm, onCancel, isLoading }: RejectFormProps) {
  const [reason, setReason] = useState("");

  return (
    <div className="animate-in fade-in slide-in-from-top-2 duration-200 rounded-lg border border-destructive/30 bg-destructive/5 p-4">
      <p className="mb-2 text-sm font-medium text-destructive">
        Rejection Reason
      </p>
      <Textarea
        placeholder="Enter rejection reason..."
        value={reason}
        onChange={(e) => setReason(e.target.value)}
        className="mb-3 min-h-24"
        disabled={isLoading}
      />
      <div className="flex items-center gap-2">
        <Button variant="ghost" size="sm" onClick={onCancel} disabled={isLoading}>
          Cancel
        </Button>
        <Button
          variant="destructive"
          size="sm"
          onClick={() => onConfirm(reason)}
          disabled={!reason.trim() || isLoading}
        >
          {isLoading ? "Rejecting..." : "Confirm Reject"}
        </Button>
      </div>
    </div>
  );
}
