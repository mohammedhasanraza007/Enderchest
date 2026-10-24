import { Link } from "react-router-dom";
import type { BreakdownEntry, Dashboard, RingName } from "../api/endpoints";
import { useRing } from "../api/queries";
import { RING_ORDER, RING_WORDS } from "../lib/dashboard";
import { Chip } from "../primitives/Chip";
import { Sheet } from "../primitives/Overlay";
import { Skeleton } from "../primitives/Skeleton";
import { ErrorState } from "./ErrorState";

// The breakdown sheet behind the rings (PAGES.md P-12): for one ring, what counts and what does
// not, each linking to its item or to Tasks. The counts in the headings are the lists' own
// lengths from the server, and they equal the ring's numbers (F-020).

interface RingSheetProps {
  ring: RingName | null;
  rings: Dashboard["rings"];
  onChoose: (ring: RingName) => void;
  onClose: () => void;
}

export function RingSheet({ ring, rings, onChoose, onClose }: RingSheetProps) {
  const sheet = useRing(ring);
  const words = ring ? RING_WORDS[ring] : null;

  return (
    <Sheet open={ring !== null} onClose={onClose} title="What counts">
      <div className="stack ring-sheet">
        <div className="chip-row" role="radiogroup" aria-label="Ring">
          {RING_ORDER.map((name) => (
            <Chip key={name} role="radio" selected={ring === name} onSelect={() => onChoose(name)}>
              {RING_WORDS[name].name} {rings[name].value ?? "—"}
            </Chip>
          ))}
        </div>
        {words ? <p className="section-note">{words.rule}</p> : null}
        {sheet.isPending ? (
          <div className="stack" aria-busy="true">
            <Skeleton height={24} width="60%" />
            <Skeleton height={44} />
            <Skeleton height={44} />
          </div>
        ) : sheet.isError ? (
          <ErrorState message={sheet.error.message} onRetry={() => void sheet.refetch()} />
        ) : sheet.data.den === 0 ? (
          <p className="ring-sheet__none">
            {sheet.data.ring === "on_time"
              ? "No tasks yet, so this ring is left out of the score."
              : "No items yet, so this ring is left out of the score."}
          </p>
        ) : (
          <>
            <p className="ring-sheet__sum">
              {sheet.data.num} of {sheet.data.den} count: {sheet.data.value}
            </p>
            <EntryList
              title="Not counted"
              entries={sheet.data.failing}
              total={sheet.data.den - sheet.data.num}
            />
            <EntryList title="Counted" entries={sheet.data.qualifying} total={sheet.data.num} />
          </>
        )}
      </div>
    </Sheet>
  );
}

function EntryList({
  title,
  entries,
  total,
}: {
  title: string;
  entries: BreakdownEntry[];
  total: number;
}) {
  if (total === 0) return null;
  return (
    <section className="ring-sheet__group">
      <h3 className="ring-sheet__title">
        {title} ({total})
      </h3>
      <ul className="ring-sheet__list">
        {entries.map((entry) => (
          <li key={`${entry.kind}-${entry.task_id ?? entry.public_id}`}>
            <Link to={entry.kind === "task" ? "/tasks" : `/items/${entry.public_id}`}>
              {entry.name}
            </Link>
            <span className="ring-sheet__note">{entry.note}</span>
          </li>
        ))}
      </ul>
      {total > entries.length ? (
        <p className="section-note">and {total - entries.length} more</p>
      ) : null}
    </section>
  );
}
