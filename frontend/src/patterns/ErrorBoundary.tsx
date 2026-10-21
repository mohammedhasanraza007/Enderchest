import { Component } from "react";
import type { ErrorInfo, ReactNode } from "react";
import { BrandMark } from "../primitives/BrandMark";
import { GlassCard } from "../primitives/Glass";

// Catches a crash while drawing a screen and shows a calm card instead of a blank page
// (PAGES.md 2, "error" state). It says what happened and what to do, and never shows a stack.

interface State {
  failed: boolean;
}

export class ErrorBoundary extends Component<{ children: ReactNode }, State> {
  override state: State = { failed: false };

  static getDerivedStateFromError(): State {
    return { failed: true };
  }

  override componentDidCatch(error: Error, info: ErrorInfo): void {
    // The details go to the browser console for the owner or Claude; the page stays plain.
    console.error("Enderchest screen crashed", error, info.componentStack);
  }

  override render(): ReactNode {
    if (!this.state.failed) return this.props.children;
    return (
      <main className="page page--narrow center-card">
        <BrandMark size={72} />
        <GlassCard title="Something went wrong" headingLevel={1}>
          <p className="stack-gap">This screen could not be drawn. Nothing was lost.</p>
          <button
            type="button"
            className="pill pill--primary"
            onClick={() => window.location.reload()}
          >
            Reload the page
          </button>
        </GlassCard>
      </main>
    );
  }
}
