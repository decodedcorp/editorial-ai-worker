"use client";

import { useState } from "react";

export function JsonPanel({ data }: { data: unknown }) {
  const [open, setOpen] = useState(false);

  return (
    <div className="rounded-lg border">
      <button
        type="button"
        onClick={() => setOpen(!open)}
        className="flex w-full items-center gap-2 px-4 py-3 text-left text-sm font-medium text-muted-foreground hover:text-foreground"
      >
        <span>{open ? "\u25BE" : "\u25B8"}</span>
        Raw JSON
      </button>
      {open && (
        <pre className="max-h-96 overflow-auto rounded-b-lg bg-slate-950 p-4 font-mono text-xs text-slate-100">
          {JSON.stringify(data, null, 2)}
        </pre>
      )}
    </div>
  );
}
