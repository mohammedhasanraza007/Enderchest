import { LinkButton } from "../../primitives/Button";
import { GlassCard } from "../../primitives/Glass";

// Settings, Data (PAGES.md P-02): the way to Trash, where deleted items wait.

export function DataSection() {
  return (
    <GlassCard title="Data">
      <div className="stack">
        <p className="section-note">
          Deleted items stay in Trash until you restore them or delete them for good.
        </p>
        <div>
          <LinkButton variant="secondary" to="/trash">
            Open Trash
          </LinkButton>
        </div>
      </div>
    </GlassCard>
  );
}
