"use client";

import { useState, useEffect, useCallback, useRef } from "react";
import { useRouter } from "next/navigation";
import { Plus, Check, Loader2, Circle, ChevronDown } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import type { TriggerResponse, PipelineStatus } from "@/lib/types";

// ---------------------------------------------------------------------------
// Pipeline step definitions
// ---------------------------------------------------------------------------

const PIPELINE_STEPS = [
  { key: "curating", label: "Curating trends" },
  { key: "sourcing", label: "Finding sources" },
  { key: "drafting", label: "Writing editorial" },
  { key: "reviewing", label: "Quality review" },
  { key: "awaiting_approval", label: "Ready for approval" },
] as const;

type Phase = "form" | "running" | "success" | "error";

const POLL_INTERVAL = 3_000;
const POLL_TIMEOUT = 180_000;

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export function NewContentModal() {
  const router = useRouter();
  const [open, setOpen] = useState(false);

  // Form state
  const [keyword, setKeyword] = useState("");
  const [category, setCategory] = useState("fashion");
  const [showAdvanced, setShowAdvanced] = useState(false);
  const [tone, setTone] = useState("");
  const [style, setStyle] = useState("");
  const [targetCeleb, setTargetCeleb] = useState("");
  const [targetBrand, setTargetBrand] = useState("");

  // Execution state
  const [phase, setPhase] = useState<Phase>("form");
  const [threadId, setThreadId] = useState<string | null>(null);
  const [currentStatus, setCurrentStatus] = useState("");
  const [errorMessages, setErrorMessages] = useState<string[]>([]);

  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const startTimeRef = useRef<number>(0);

  // ---------------------------------------------------------------------------
  // Reset form
  // ---------------------------------------------------------------------------

  const resetForm = useCallback(() => {
    setKeyword("");
    setCategory("fashion");
    setShowAdvanced(false);
    setTone("");
    setStyle("");
    setTargetCeleb("");
    setTargetBrand("");
    setPhase("form");
    setThreadId(null);
    setCurrentStatus("");
    setErrorMessages([]);
  }, []);

  // ---------------------------------------------------------------------------
  // Polling
  // ---------------------------------------------------------------------------

  const stopPolling = useCallback(() => {
    if (pollRef.current) {
      clearInterval(pollRef.current);
      pollRef.current = null;
    }
  }, []);

  const pollStatus = useCallback(
    async (tid: string) => {
      try {
        const res = await fetch(`/api/pipeline/status/${tid}`);
        if (!res.ok) {
          // Thread might not be registered yet; ignore transient errors
          return;
        }
        const data: PipelineStatus = await res.json();
        setCurrentStatus(data.pipeline_status);

        if (
          data.pipeline_status === "awaiting_approval" ||
          data.pipeline_status === "completed"
        ) {
          stopPolling();
          setPhase("success");
          // Give a brief moment then close and refresh
          setTimeout(() => {
            setOpen(false);
            resetForm();
            router.refresh();
          }, 1_200);
          return;
        }

        if (data.pipeline_status === "failed") {
          stopPolling();
          setPhase("error");
          setErrorMessages(
            data.error_log.length > 0
              ? data.error_log
              : ["Pipeline execution failed."]
          );
          return;
        }

        // Timeout check
        if (Date.now() - startTimeRef.current > POLL_TIMEOUT) {
          stopPolling();
          setPhase("error");
          setErrorMessages([
            "Pipeline timed out after 3 minutes. Check the server logs.",
          ]);
        }
      } catch {
        // Network error during polling — don't crash, just wait for next tick
      }
    },
    [stopPolling, resetForm, router]
  );

  // Cleanup on unmount
  useEffect(() => {
    return () => stopPolling();
  }, [stopPolling]);

  // ---------------------------------------------------------------------------
  // Submit
  // ---------------------------------------------------------------------------

  const handleSubmit = async () => {
    if (!keyword.trim()) return;

    setPhase("running");
    setErrorMessages([]);
    startTimeRef.current = Date.now();

    const body = {
      seed_keyword: keyword.trim(),
      category,
      ...(tone ? { tone } : {}),
      ...(style ? { style } : {}),
      ...(targetCeleb ? { target_celeb: targetCeleb } : {}),
      ...(targetBrand ? { target_brand: targetBrand } : {}),
    };

    try {
      const res = await fetch("/api/pipeline/trigger", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });

      if (!res.ok) {
        const errData = await res.json().catch(() => null);
        setPhase("error");
        setErrorMessages([
          errData?.detail ?? `Trigger failed (${res.status})`,
        ]);
        return;
      }

      const data: TriggerResponse = await res.json();
      setThreadId(data.thread_id);

      // Start polling
      pollRef.current = setInterval(
        () => pollStatus(data.thread_id),
        POLL_INTERVAL
      );
      // Immediate first poll
      pollStatus(data.thread_id);
    } catch {
      setPhase("error");
      setErrorMessages(["Network error. Is the server running?"]);
    }
  };

  // ---------------------------------------------------------------------------
  // Step indicator helpers
  // ---------------------------------------------------------------------------

  const getStepIndex = (status: string) =>
    PIPELINE_STEPS.findIndex((s) => s.key === status);

  const renderStepIcon = (stepIndex: number, activeIndex: number) => {
    if (stepIndex < activeIndex) {
      return <Check className="h-4 w-4 text-green-600" />;
    }
    if (stepIndex === activeIndex) {
      return <Loader2 className="h-4 w-4 animate-spin text-blue-600" />;
    }
    return <Circle className="h-4 w-4 text-muted-foreground/40" />;
  };

  // ---------------------------------------------------------------------------
  // Render
  // ---------------------------------------------------------------------------

  const activeIndex = getStepIndex(currentStatus);

  return (
    <Dialog
      open={open}
      onOpenChange={(v) => {
        setOpen(v);
        if (!v) resetForm();
      }}
    >
      <DialogTrigger asChild>
        <Button>
          <Plus className="mr-2 h-4 w-4" />
          New Content
        </Button>
      </DialogTrigger>

      <DialogContent className="sm:max-w-[480px]">
        <DialogHeader>
          <DialogTitle>Create New Content</DialogTitle>
          <DialogDescription>
            Enter a keyword to start the editorial pipeline.
          </DialogDescription>
        </DialogHeader>

        {/* ---------- Form Phase ---------- */}
        {phase === "form" && (
          <div className="space-y-4 pt-2">
            <div className="space-y-2">
              <Label htmlFor="keyword">Keyword *</Label>
              <Input
                id="keyword"
                placeholder="e.g., Y2K fashion revival"
                value={keyword}
                onChange={(e) => setKeyword(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === "Enter") handleSubmit();
                }}
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="category">Category</Label>
              <Select value={category} onValueChange={setCategory}>
                <SelectTrigger id="category">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="fashion">Fashion</SelectItem>
                  <SelectItem value="beauty">Beauty</SelectItem>
                  <SelectItem value="lifestyle">Lifestyle</SelectItem>
                </SelectContent>
              </Select>
            </div>

            {/* Advanced options toggle */}
            <button
              type="button"
              className="flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground transition-colors"
              onClick={() => setShowAdvanced(!showAdvanced)}
            >
              <ChevronDown
                className={`h-4 w-4 transition-transform ${showAdvanced ? "rotate-180" : ""}`}
              />
              Advanced Options
            </button>

            {showAdvanced && (
              <div className="space-y-3 rounded-md border p-3">
                <div className="space-y-1">
                  <Label htmlFor="tone" className="text-xs">
                    Tone
                  </Label>
                  <Input
                    id="tone"
                    placeholder="e.g., editorial, casual, luxury"
                    value={tone}
                    onChange={(e) => setTone(e.target.value)}
                  />
                </div>
                <div className="space-y-1">
                  <Label htmlFor="style" className="text-xs">
                    Style
                  </Label>
                  <Input
                    id="style"
                    placeholder="e.g., minimalist, bold, streetwear"
                    value={style}
                    onChange={(e) => setStyle(e.target.value)}
                  />
                </div>
                <div className="space-y-1">
                  <Label htmlFor="targetCeleb" className="text-xs">
                    Target Celeb
                  </Label>
                  <Input
                    id="targetCeleb"
                    placeholder="e.g., NewJeans, aespa"
                    value={targetCeleb}
                    onChange={(e) => setTargetCeleb(e.target.value)}
                  />
                </div>
                <div className="space-y-1">
                  <Label htmlFor="targetBrand" className="text-xs">
                    Target Brand
                  </Label>
                  <Input
                    id="targetBrand"
                    placeholder="e.g., Gucci, Chanel"
                    value={targetBrand}
                    onChange={(e) => setTargetBrand(e.target.value)}
                  />
                </div>
              </div>
            )}

            <Button
              className="w-full"
              onClick={handleSubmit}
              disabled={!keyword.trim()}
            >
              Start Pipeline
            </Button>
          </div>
        )}

        {/* ---------- Running Phase ---------- */}
        {phase === "running" && (
          <div className="space-y-4 pt-2">
            <p className="text-sm text-muted-foreground">
              Running pipeline for{" "}
              <span className="font-medium text-foreground">{keyword}</span>
              ...
            </p>
            <div className="space-y-3">
              {PIPELINE_STEPS.map((step, idx) => (
                <div key={step.key} className="flex items-center gap-3">
                  {renderStepIcon(idx, activeIndex)}
                  <span
                    className={`text-sm ${
                      idx < activeIndex
                        ? "text-green-600"
                        : idx === activeIndex
                          ? "font-medium text-foreground"
                          : "text-muted-foreground/60"
                    }`}
                  >
                    {step.label}
                  </span>
                </div>
              ))}
            </div>
            {threadId && (
              <p className="text-xs text-muted-foreground">
                Thread: {threadId}
              </p>
            )}
          </div>
        )}

        {/* ---------- Success Phase ---------- */}
        {phase === "success" && (
          <div className="flex flex-col items-center gap-3 py-6">
            <div className="flex h-12 w-12 items-center justify-center rounded-full bg-green-100">
              <Check className="h-6 w-6 text-green-600" />
            </div>
            <p className="text-sm font-medium">
              Content created successfully!
            </p>
            <p className="text-xs text-muted-foreground">
              Redirecting to contents list...
            </p>
          </div>
        )}

        {/* ---------- Error Phase ---------- */}
        {phase === "error" && (
          <div className="space-y-4 pt-2">
            <div className="rounded-md border border-destructive/50 bg-destructive/5 p-3">
              <p className="text-sm font-medium text-destructive">
                Pipeline Error
              </p>
              <ul className="mt-2 space-y-1">
                {errorMessages.map((msg, i) => (
                  <li key={i} className="text-xs text-destructive/80">
                    {msg}
                  </li>
                ))}
              </ul>
            </div>
            <Button variant="outline" className="w-full" onClick={resetForm}>
              Try Again
            </Button>
          </div>
        )}
      </DialogContent>
    </Dialog>
  );
}
