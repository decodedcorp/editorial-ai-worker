import type { ReactNode } from "react";

interface StickyActionBarProps {
  children: ReactNode;
}

export function StickyActionBar({ children }: StickyActionBarProps) {
  return (
    <div className="sticky top-0 z-50 bg-white/95 backdrop-blur border-b">
      <div className="flex items-center gap-4 px-6 py-3">
        {children}
      </div>
    </div>
  );
}
