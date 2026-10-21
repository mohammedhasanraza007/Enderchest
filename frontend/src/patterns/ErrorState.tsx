import { Button } from "../primitives/Button";
import { InnerPanel } from "../primitives/Glass";

// The "error" state of a list or page (PAGES.md 2): what happened, what to do, and a Retry
// button that repeats the same request.

export function ErrorState({ message, onRetry }: { message: string; onRetry: () => void }) {
  return (
    <InnerPanel role="alert" className="error-state">
      <p>{message}</p>
      <Button variant="secondary" onClick={onRetry}>
        Retry
      </Button>
    </InnerPanel>
  );
}
