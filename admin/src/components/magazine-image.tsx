"use client";

import { useState } from "react";

interface MagazineImageProps {
  src: string;
  alt: string;
  aspectRatio?: string;
  className?: string;
  gradientFrom?: string;
  gradientTo?: string;
  priority?: boolean;
}

export function MagazineImage({
  src,
  alt,
  aspectRatio = "16/9",
  className = "",
  gradientFrom = "#1a1a2e",
  gradientTo = "#e94560",
  priority = false,
}: MagazineImageProps) {
  const [isLoaded, setIsLoaded] = useState(false);
  const [hasError, setHasError] = useState(!src);

  return (
    <div
      className={`relative overflow-hidden rounded-lg ${className}`}
      style={{ aspectRatio }}
    >
      {/* Gradient fallback — always present behind image */}
      <div
        className="absolute inset-0"
        style={{
          background: `linear-gradient(135deg, ${gradientFrom}, ${gradientTo})`,
        }}
      />

      {/* Image — hidden when error or no src */}
      {!hasError && (
        <img
          src={src}
          alt={alt}
          loading={priority ? "eager" : "lazy"}
          onLoad={() => setIsLoaded(true)}
          onError={() => setHasError(true)}
          className={`absolute inset-0 h-full w-full object-cover transition-all duration-700 ease-out ${
            isLoaded ? "scale-100 blur-0" : "scale-105 blur-sm"
          }`}
        />
      )}
    </div>
  );
}
