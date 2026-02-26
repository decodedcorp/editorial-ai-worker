"use client";

import { createContext, useContext } from "react";
import type { DesignSpec } from "@/lib/types";

const DesignSpecContext = createContext<DesignSpec | null>(null);

export function DesignSpecProvider({
  designSpec,
  children,
}: {
  designSpec: DesignSpec | null;
  children: React.ReactNode;
}) {
  return (
    <DesignSpecContext.Provider value={designSpec}>
      {children}
    </DesignSpecContext.Provider>
  );
}

export function useDesignSpec(): DesignSpec | null {
  return useContext(DesignSpecContext);
}
