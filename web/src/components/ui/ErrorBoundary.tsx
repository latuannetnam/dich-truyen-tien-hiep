"use client";

import { Component, ReactNode } from "react";
import { AlertTriangle, RotateCcw } from "lucide-react";

interface Props {
  children: ReactNode;
  fallback?: ReactNode;
}

interface State {
  hasError: boolean;
  error: Error | null;
}

export default class ErrorBoundary extends Component<Props, State> {
  state: State = { hasError: false, error: null };

  static getDerivedStateFromError(error: Error) {
    return { hasError: true, error };
  }

  render() {
    if (this.state.hasError) {
      return (
        this.props.fallback || (
          <div className="flex flex-col items-center justify-center p-12 text-center animate-fade-in">
            <AlertTriangle
              size={48}
              className="text-[var(--color-warning)] mb-4"
            />
            <h2 className="text-lg font-semibold text-[var(--text-primary)] mb-2">
              Something went wrong
            </h2>
            <p className="text-[var(--text-secondary)] text-sm mb-4 max-w-md">
              {this.state.error?.message || "An unexpected error occurred"}
            </p>
            <button
              onClick={() => this.setState({ hasError: false, error: null })}
              className="inline-flex items-center gap-2 px-4 py-2 rounded-lg
                bg-[var(--color-primary)] text-white text-sm cursor-pointer
                hover:bg-[var(--color-primary-hover)] transition-colors"
            >
              <RotateCcw size={14} />
              Try Again
            </button>
          </div>
        )
      );
    }
    return this.props.children;
  }
}
