"use client";

import React from "react";

interface BlockErrorBoundaryProps {
  blockType: string;
  blockData: unknown;
  children: React.ReactNode;
}

interface BlockErrorBoundaryState {
  hasError: boolean;
  error: Error | null;
}

export class BlockErrorBoundary extends React.Component<
  BlockErrorBoundaryProps,
  BlockErrorBoundaryState
> {
  constructor(props: BlockErrorBoundaryProps) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error: Error): BlockErrorBoundaryState {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, errorInfo: React.ErrorInfo): void {
    console.error(
      `[BlockErrorBoundary] Error in block "${this.props.blockType}":`,
      error,
      errorInfo,
    );
  }

  render() {
    if (this.state.hasError) {
      const { blockType, blockData } = this.props;
      const message = this.state.error?.message ?? "Unknown error";

      return (
        <div className="rounded-lg border border-amber-300 bg-amber-50 p-4">
          <p className="text-sm font-medium text-amber-800">
            <span className="font-mono">{blockType}</span>: {message}
          </p>
          <details className="mt-2">
            <summary className="cursor-pointer text-xs text-amber-600 hover:text-amber-800">
              View raw data
            </summary>
            <pre className="mt-2 max-h-48 overflow-auto rounded bg-amber-100 p-2 text-xs text-amber-900">
              {JSON.stringify(blockData, null, 2)}
            </pre>
          </details>
        </div>
      );
    }

    return this.props.children;
  }
}
