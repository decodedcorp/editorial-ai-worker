"use client";

import { useState, useEffect, useCallback, useRef } from "react";
import { useRouter } from "next/navigation";
import {
  Plus,
  Check,
  Loader2,
  Circle,
  ChevronDown,
  Search,
  Eye,
  Flame,
  X,
} from "lucide-react";
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
import type {
  TriggerResponse,
  PipelineStatus,
  PostSource,
  CelebSource,
  ProductSource,
  SourceSearchResponse,
} from "@/lib/types";

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

const PIPELINE_STEPS_DB = [
  { key: "curating", label: "Loading sources" },
  { key: "sourcing", label: "Preparing context" },
  { key: "drafting", label: "Writing editorial" },
  { key: "reviewing", label: "Quality review" },
  { key: "awaiting_approval", label: "Ready for approval" },
] as const;

const PIPELINE_STEPS_AI_DB = [
  { key: "curating", label: "Expanding search terms" },
  { key: "sourcing", label: "Searching DB" },
  { key: "drafting", label: "Writing editorial" },
  { key: "reviewing", label: "Quality review" },
  { key: "awaiting_approval", label: "Ready for approval" },
] as const;

type Phase = "form" | "running" | "success" | "error";
type ContentMode = "ai_curation" | "db_source" | "ai_db_search";

const POLL_INTERVAL = 3_000;
const POLL_TIMEOUT = 180_000;

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export function NewContentModal() {
  const router = useRouter();
  const [open, setOpen] = useState(false);

  // Mode
  const [mode, setMode] = useState<ContentMode>("ai_curation");

  // Form state (shared)
  const [keyword, setKeyword] = useState("");
  const [category, setCategory] = useState("fashion");
  const [showAdvanced, setShowAdvanced] = useState(false);
  const [tone, setTone] = useState("");
  const [style, setStyle] = useState("");
  const [targetCeleb, setTargetCeleb] = useState("");
  const [targetBrand, setTargetBrand] = useState("");

  // DB Source state
  const [searchQuery, setSearchQuery] = useState("");
  const [searchResults, setSearchResults] = useState<SourceSearchResponse>({});
  const [isSearching, setIsSearching] = useState(false);
  const [selectedPosts, setSelectedPosts] = useState<Set<string>>(new Set());
  const [selectedCelebs, setSelectedCelebs] = useState<Set<string>>(new Set());
  const [selectedProducts, setSelectedProducts] = useState<Set<string>>(
    new Set()
  );

  // Execution state
  const [phase, setPhase] = useState<Phase>("form");
  const [threadId, setThreadId] = useState<string | null>(null);
  const [currentStatus, setCurrentStatus] = useState("");
  const [errorMessages, setErrorMessages] = useState<string[]>([]);

  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const startTimeRef = useRef<number>(0);
  const searchTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);

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
    setMode("ai_curation");
    setSearchQuery("");
    setSearchResults({});
    setSelectedPosts(new Set());
    setSelectedCelebs(new Set());
    setSelectedProducts(new Set());
    setPhase("form");
    setThreadId(null);
    setCurrentStatus("");
    setErrorMessages([]);
  }, []);

  // ---------------------------------------------------------------------------
  // DB Source Search
  // ---------------------------------------------------------------------------

  const doSearch = useCallback(async (q: string) => {
    if (!q.trim()) {
      setSearchResults({});
      return;
    }
    setIsSearching(true);
    try {
      const res = await fetch(
        `/api/sources/search?q=${encodeURIComponent(q.trim())}&type=all&limit=10`
      );
      if (res.ok) {
        const data: SourceSearchResponse = await res.json();
        setSearchResults(data);
      }
    } catch {
      // Silently handle network errors during search
    } finally {
      setIsSearching(false);
    }
  }, []);

  // Debounced search
  useEffect(() => {
    if (mode !== "db_source") return;
    if (searchTimeoutRef.current) clearTimeout(searchTimeoutRef.current);
    searchTimeoutRef.current = setTimeout(() => doSearch(searchQuery), 400);
    return () => {
      if (searchTimeoutRef.current) clearTimeout(searchTimeoutRef.current);
    };
  }, [searchQuery, mode, doSearch]);

  // ---------------------------------------------------------------------------
  // Selection helpers
  // ---------------------------------------------------------------------------

  const togglePost = (id: string) =>
    setSelectedPosts((prev) => {
      const next = new Set(prev);
      next.has(id) ? next.delete(id) : next.add(id);
      return next;
    });

  const toggleCeleb = (id: string) =>
    setSelectedCelebs((prev) => {
      const next = new Set(prev);
      next.has(id) ? next.delete(id) : next.add(id);
      return next;
    });

  const toggleProduct = (id: string) =>
    setSelectedProducts((prev) => {
      const next = new Set(prev);
      next.has(id) ? next.delete(id) : next.add(id);
      return next;
    });

  const totalSelected =
    selectedPosts.size + selectedCelebs.size + selectedProducts.size;

  // Auto-generate keyword from selections for db_source mode
  const dbSourceKeyword = (() => {
    const posts = searchResults.posts?.filter((p) => selectedPosts.has(p.id));
    if (posts && posts.length > 0) {
      const groups = [
        ...new Set(posts.map((p) => p.group_name).filter(Boolean)),
      ];
      return groups.join(" & ") || posts[0].artist_name;
    }
    const celebs = searchResults.celebs?.filter((c) =>
      selectedCelebs.has(c.id)
    );
    if (celebs && celebs.length > 0) return celebs[0].name;
    return searchQuery || "DB Source";
  })();

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
        if (!res.ok) return;
        const data: PipelineStatus = await res.json();
        setCurrentStatus(data.pipeline_status);

        if (
          data.pipeline_status === "awaiting_approval" ||
          data.pipeline_status === "completed"
        ) {
          stopPolling();
          setPhase("success");
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

        if (Date.now() - startTimeRef.current > POLL_TIMEOUT) {
          stopPolling();
          setPhase("error");
          setErrorMessages([
            "Pipeline timed out after 3 minutes. Check the server logs.",
          ]);
        }
      } catch {
        // Network error during polling
      }
    },
    [stopPolling, resetForm, router]
  );

  useEffect(() => {
    return () => stopPolling();
  }, [stopPolling]);

  // ---------------------------------------------------------------------------
  // Submit
  // ---------------------------------------------------------------------------

  const handleSubmit = async () => {
    if ((mode === "ai_curation" || mode === "ai_db_search") && !keyword.trim()) return;
    if (mode === "db_source" && totalSelected === 0) return;

    setPhase("running");
    setErrorMessages([]);
    startTimeRef.current = Date.now();

    const body =
      mode === "db_source"
        ? {
            seed_keyword: dbSourceKeyword,
            category,
            mode: "db_source" as const,
            selected_posts: [...selectedPosts],
            selected_celebs: [...selectedCelebs],
            selected_products: [...selectedProducts],
            ...(tone ? { tone } : {}),
            ...(style ? { style } : {}),
          }
        : mode === "ai_db_search"
          ? {
              seed_keyword: keyword.trim(),
              category,
              mode: "ai_db_search" as const,
              ...(tone ? { tone } : {}),
              ...(style ? { style } : {}),
            }
          : {
              seed_keyword: keyword.trim(),
              category,
              mode: "ai_curation" as const,
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
      pollRef.current = setInterval(
        () => pollStatus(data.thread_id),
        POLL_INTERVAL
      );
      pollStatus(data.thread_id);
    } catch {
      setPhase("error");
      setErrorMessages(["Network error. Is the server running?"]);
    }
  };

  // ---------------------------------------------------------------------------
  // Step indicator helpers
  // ---------------------------------------------------------------------------

  const steps = mode === "db_source" ? PIPELINE_STEPS_DB : mode === "ai_db_search" ? PIPELINE_STEPS_AI_DB : PIPELINE_STEPS;
  const getStepIndex = (status: string) =>
    steps.findIndex((s) => s.key === status);

  const renderStepIcon = (stepIndex: number, activeIndex: number) => {
    if (stepIndex < activeIndex)
      return <Check className="h-4 w-4 text-green-600" />;
    if (stepIndex === activeIndex)
      return <Loader2 className="h-4 w-4 animate-spin text-blue-600" />;
    return <Circle className="h-4 w-4 text-muted-foreground/40" />;
  };

  const activeIndex = getStepIndex(currentStatus);

  // ---------------------------------------------------------------------------
  // Render
  // ---------------------------------------------------------------------------

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

      <DialogContent className="sm:max-w-[560px] max-h-[85vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>Create New Content</DialogTitle>
          <DialogDescription>
            Choose a source mode to start the editorial pipeline.
          </DialogDescription>
        </DialogHeader>

        {/* ---------- Form Phase ---------- */}
        {phase === "form" && (
          <div className="space-y-4 pt-2">
            {/* Mode Toggle */}
            <div className="flex rounded-lg border p-1 gap-1">
              <button
                type="button"
                className={`flex-1 rounded-md px-3 py-2 text-sm font-medium transition-colors ${
                  mode === "ai_curation"
                    ? "bg-primary text-primary-foreground"
                    : "text-muted-foreground hover:text-foreground"
                }`}
                onClick={() => setMode("ai_curation")}
              >
                AI Curation
              </button>
              <button
                type="button"
                className={`flex-1 rounded-md px-3 py-2 text-sm font-medium transition-colors ${
                  mode === "ai_db_search"
                    ? "bg-teal-600 text-white"
                    : "text-muted-foreground hover:text-foreground"
                }`}
                onClick={() => setMode("ai_db_search")}
              >
                AI DB Search
              </button>
              <button
                type="button"
                className={`flex-1 rounded-md px-3 py-2 text-sm font-medium transition-colors ${
                  mode === "db_source"
                    ? "bg-primary text-primary-foreground"
                    : "text-muted-foreground hover:text-foreground"
                }`}
                onClick={() => setMode("db_source")}
              >
                DB Source
              </button>
            </div>

            {/* ---- AI Curation Mode ---- */}
            {mode === "ai_curation" && (
              <>
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

                {/* Advanced options */}
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
              </>
            )}

            {/* ---- AI DB Search Mode ---- */}
            {mode === "ai_db_search" && (
              <>
                <div className="space-y-2">
                  <Label htmlFor="keyword-db">Keyword *</Label>
                  <Input
                    id="keyword-db"
                    placeholder="e.g., 선글라스 트렌드, NewJeans 공항패션"
                    value={keyword}
                    onChange={(e) => setKeyword(e.target.value)}
                    onKeyDown={(e) => {
                      if (e.key === "Enter") handleSubmit();
                    }}
                  />
                  <p className="text-xs text-muted-foreground">
                    AI will expand your keyword into optimized search terms and
                    find matching content from our database.
                  </p>
                </div>

                <div className="space-y-2">
                  <Label htmlFor="category-db">Category</Label>
                  <Select value={category} onValueChange={setCategory}>
                    <SelectTrigger id="category-db">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="fashion">Fashion</SelectItem>
                      <SelectItem value="beauty">Beauty</SelectItem>
                      <SelectItem value="lifestyle">Lifestyle</SelectItem>
                    </SelectContent>
                  </Select>
                </div>

                {/* Advanced options */}
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
                      <Label htmlFor="tone-db" className="text-xs">
                        Tone
                      </Label>
                      <Input
                        id="tone-db"
                        placeholder="e.g., editorial, casual, luxury"
                        value={tone}
                        onChange={(e) => setTone(e.target.value)}
                      />
                    </div>
                    <div className="space-y-1">
                      <Label htmlFor="style-db" className="text-xs">
                        Style
                      </Label>
                      <Input
                        id="style-db"
                        placeholder="e.g., minimalist, bold, streetwear"
                        value={style}
                        onChange={(e) => setStyle(e.target.value)}
                      />
                    </div>
                  </div>
                )}

                <Button
                  className="w-full"
                  onClick={handleSubmit}
                  disabled={!keyword.trim()}
                >
                  Search DB with AI
                </Button>
              </>
            )}

            {/* ---- DB Source Mode ---- */}
            {mode === "db_source" && (
              <>
                {/* Search bar */}
                <div className="relative">
                  <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                  <Input
                    className="pl-9"
                    placeholder="Search celebs, groups, brands..."
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                  />
                  {isSearching && (
                    <Loader2 className="absolute right-3 top-1/2 -translate-y-1/2 h-4 w-4 animate-spin text-muted-foreground" />
                  )}
                </div>

                {/* Search results */}
                <div className="space-y-3 max-h-[340px] overflow-y-auto">
                  {/* Posts */}
                  {(searchResults.posts?.length ?? 0) > 0 && (
                    <div>
                      <p className="text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-2">
                        Posts ({searchResults.posts!.length})
                      </p>
                      <div className="space-y-1.5">
                        {searchResults.posts!.map((post) => (
                          <PostResultItem
                            key={post.id}
                            post={post}
                            selected={selectedPosts.has(post.id)}
                            onToggle={() => togglePost(post.id)}
                          />
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Celebs */}
                  {(searchResults.celebs?.length ?? 0) > 0 && (
                    <div>
                      <p className="text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-2">
                        Celebs ({searchResults.celebs!.length})
                      </p>
                      <div className="space-y-1.5">
                        {searchResults.celebs!.map((celeb) => (
                          <CelebResultItem
                            key={celeb.id}
                            celeb={celeb}
                            selected={selectedCelebs.has(celeb.id)}
                            onToggle={() => toggleCeleb(celeb.id)}
                          />
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Products */}
                  {(searchResults.products?.length ?? 0) > 0 && (
                    <div>
                      <p className="text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-2">
                        Products ({searchResults.products!.length})
                      </p>
                      <div className="space-y-1.5">
                        {searchResults.products!.map((product) => (
                          <ProductResultItem
                            key={product.id}
                            product={product}
                            selected={selectedProducts.has(product.id)}
                            onToggle={() => toggleProduct(product.id)}
                          />
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Empty state */}
                  {searchQuery &&
                    !isSearching &&
                    !searchResults.posts?.length &&
                    !searchResults.celebs?.length &&
                    !searchResults.products?.length && (
                      <p className="text-sm text-muted-foreground text-center py-6">
                        No results for &quot;{searchQuery}&quot;
                      </p>
                    )}

                  {!searchQuery && (
                    <p className="text-sm text-muted-foreground text-center py-6">
                      Search to browse DB sources
                    </p>
                  )}
                </div>

                {/* Selection summary & options */}
                {totalSelected > 0 && (
                  <div className="space-y-3 rounded-md border bg-muted/30 p-3">
                    <div className="flex items-center justify-between">
                      <p className="text-sm font-medium">
                        Selected:{" "}
                        {selectedPosts.size > 0 && (
                          <span className="text-blue-600">
                            {selectedPosts.size} posts
                          </span>
                        )}
                        {selectedPosts.size > 0 &&
                          (selectedCelebs.size > 0 ||
                            selectedProducts.size > 0) &&
                          " | "}
                        {selectedCelebs.size > 0 && (
                          <span className="text-purple-600">
                            {selectedCelebs.size} celebs
                          </span>
                        )}
                        {selectedCelebs.size > 0 &&
                          selectedProducts.size > 0 &&
                          " | "}
                        {selectedProducts.size > 0 && (
                          <span className="text-amber-600">
                            {selectedProducts.size} products
                          </span>
                        )}
                      </p>
                      <button
                        type="button"
                        className="text-xs text-muted-foreground hover:text-foreground"
                        onClick={() => {
                          setSelectedPosts(new Set());
                          setSelectedCelebs(new Set());
                          setSelectedProducts(new Set());
                        }}
                      >
                        <X className="h-3 w-3" />
                      </button>
                    </div>

                    <div className="flex gap-2">
                      <div className="flex-1">
                        <Label className="text-xs">Category</Label>
                        <Select value={category} onValueChange={setCategory}>
                          <SelectTrigger className="h-8 text-xs">
                            <SelectValue />
                          </SelectTrigger>
                          <SelectContent>
                            <SelectItem value="fashion">Fashion</SelectItem>
                            <SelectItem value="beauty">Beauty</SelectItem>
                            <SelectItem value="lifestyle">Lifestyle</SelectItem>
                          </SelectContent>
                        </Select>
                      </div>
                    </div>

                    {/* Advanced for db_source */}
                    <button
                      type="button"
                      className="flex items-center gap-1 text-xs text-muted-foreground hover:text-foreground transition-colors"
                      onClick={() => setShowAdvanced(!showAdvanced)}
                    >
                      <ChevronDown
                        className={`h-3 w-3 transition-transform ${showAdvanced ? "rotate-180" : ""}`}
                      />
                      Advanced Options
                    </button>
                    {showAdvanced && (
                      <div className="grid grid-cols-2 gap-2">
                        <div>
                          <Label className="text-xs">Tone</Label>
                          <Input
                            className="h-8 text-xs"
                            placeholder="editorial, luxury..."
                            value={tone}
                            onChange={(e) => setTone(e.target.value)}
                          />
                        </div>
                        <div>
                          <Label className="text-xs">Style</Label>
                          <Input
                            className="h-8 text-xs"
                            placeholder="minimalist, bold..."
                            value={style}
                            onChange={(e) => setStyle(e.target.value)}
                          />
                        </div>
                      </div>
                    )}
                  </div>
                )}

                <Button
                  className="w-full"
                  onClick={handleSubmit}
                  disabled={totalSelected === 0}
                >
                  Start Pipeline ({totalSelected} sources)
                </Button>
              </>
            )}
          </div>
        )}

        {/* ---------- Running Phase ---------- */}
        {phase === "running" && (
          <div className="space-y-4 pt-2">
            <p className="text-sm text-muted-foreground">
              Running pipeline
              {mode === "ai_db_search"
                ? ` searching DB for "${keyword}"`
                : mode === "db_source"
                  ? ` with ${totalSelected} selected sources`
                  : ` for "${keyword}"`}
              ...
            </p>
            <div className="space-y-3">
              {steps.map((step, idx) => (
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
            <p className="text-sm font-medium">Content created successfully!</p>
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

// ---------------------------------------------------------------------------
// Sub-components for search result items
// ---------------------------------------------------------------------------

function PostResultItem({
  post,
  selected,
  onToggle,
}: {
  post: PostSource;
  selected: boolean;
  onToggle: () => void;
}) {
  const brands = [
    ...new Set(post.solutions.map((s) => s.brand).filter(Boolean)),
  ];
  return (
    <button
      type="button"
      onClick={onToggle}
      className={`w-full text-left rounded-md border p-2.5 transition-colors ${
        selected
          ? "border-blue-500 bg-blue-50 dark:bg-blue-950/30"
          : "border-border hover:border-foreground/20"
      }`}
    >
      <div className="flex items-start gap-2">
        <div
          className={`mt-0.5 h-4 w-4 rounded border flex items-center justify-center flex-shrink-0 ${
            selected
              ? "bg-blue-500 border-blue-500"
              : "border-muted-foreground/30"
          }`}
        >
          {selected && <Check className="h-3 w-3 text-white" />}
        </div>
        <div className="min-w-0 flex-1">
          <p className="text-sm font-medium truncate">
            {post.artist_name} - {post.title}
          </p>
          <div className="flex items-center gap-3 mt-0.5">
            <span className="text-xs text-muted-foreground flex items-center gap-0.5">
              <Eye className="h-3 w-3" />
              {(post.view_count / 1000).toFixed(0)}K
            </span>
            <span className="text-xs text-muted-foreground flex items-center gap-0.5">
              <Flame className="h-3 w-3" />
              {post.trending_score}
            </span>
            <span className="text-xs text-muted-foreground">
              {post.context}
            </span>
          </div>
          {post.solutions.length > 0 && (
            <div className="flex flex-wrap gap-1 mt-1">
              {post.solutions.map((sol, i) => (
                <span
                  key={i}
                  className="inline-flex items-center text-[10px] rounded-full bg-muted px-1.5 py-0.5"
                >
                  {sol.title}
                </span>
              ))}
            </div>
          )}
          {brands.length > 0 && (
            <p className="text-[10px] text-muted-foreground mt-0.5">
              {brands.join(", ")}
            </p>
          )}
        </div>
      </div>
    </button>
  );
}

function CelebResultItem({
  celeb,
  selected,
  onToggle,
}: {
  celeb: CelebSource;
  selected: boolean;
  onToggle: () => void;
}) {
  return (
    <button
      type="button"
      onClick={onToggle}
      className={`w-full text-left rounded-md border p-2.5 transition-colors ${
        selected
          ? "border-purple-500 bg-purple-50 dark:bg-purple-950/30"
          : "border-border hover:border-foreground/20"
      }`}
    >
      <div className="flex items-start gap-2">
        <div
          className={`mt-0.5 h-4 w-4 rounded border flex items-center justify-center flex-shrink-0 ${
            selected
              ? "bg-purple-500 border-purple-500"
              : "border-muted-foreground/30"
          }`}
        >
          {selected && <Check className="h-3 w-3 text-white" />}
        </div>
        <div className="min-w-0 flex-1">
          <p className="text-sm font-medium">
            {celeb.name}
            {celeb.name_en && (
              <span className="text-muted-foreground font-normal ml-1">
                ({celeb.name_en})
              </span>
            )}
          </p>
          {celeb.tags && celeb.tags.length > 0 && (
            <div className="flex flex-wrap gap-1 mt-0.5">
              {celeb.tags.slice(0, 5).map((tag, i) => (
                <span
                  key={i}
                  className="inline-flex text-[10px] rounded-full bg-muted px-1.5 py-0.5"
                >
                  {tag}
                </span>
              ))}
            </div>
          )}
        </div>
      </div>
    </button>
  );
}

function ProductResultItem({
  product,
  selected,
  onToggle,
}: {
  product: ProductSource;
  selected: boolean;
  onToggle: () => void;
}) {
  return (
    <button
      type="button"
      onClick={onToggle}
      className={`w-full text-left rounded-md border p-2.5 transition-colors ${
        selected
          ? "border-amber-500 bg-amber-50 dark:bg-amber-950/30"
          : "border-border hover:border-foreground/20"
      }`}
    >
      <div className="flex items-start gap-2">
        <div
          className={`mt-0.5 h-4 w-4 rounded border flex items-center justify-center flex-shrink-0 ${
            selected
              ? "bg-amber-500 border-amber-500"
              : "border-muted-foreground/30"
          }`}
        >
          {selected && <Check className="h-3 w-3 text-white" />}
        </div>
        <div className="min-w-0 flex-1">
          <p className="text-sm font-medium">{product.name}</p>
          <div className="flex items-center gap-2 mt-0.5">
            {product.brand && (
              <span className="text-xs text-muted-foreground">
                {product.brand}
              </span>
            )}
            {product.price && (
              <span className="text-xs text-muted-foreground">
                {new Intl.NumberFormat("ko-KR", {
                  style: "currency",
                  currency: "KRW",
                  maximumFractionDigits: 0,
                }).format(product.price)}
              </span>
            )}
            {product.category && (
              <span className="text-[10px] rounded-full bg-muted px-1.5 py-0.5">
                {product.category}
              </span>
            )}
          </div>
        </div>
      </div>
    </button>
  );
}
