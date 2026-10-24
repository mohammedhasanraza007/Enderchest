import { useState } from "react";
import { Link } from "react-router-dom";
import { api, fileUrl } from "../api/endpoints";
import type { Draft } from "../api/endpoints";
import { useDrafts, useProfile, useRefreshInventory } from "../api/queries";
import { usePageTitle } from "../hooks/usePageTitle";
import { formatMoment } from "../lib/format";
import { ErrorState } from "../patterns/ErrorState";
import { Button, LinkButton } from "../primitives/Button";
import { GlassCard } from "../primitives/Glass";
import { Skeleton } from "../primitives/Skeleton";

// P-07, the review queue: photos taken or uploaded that are not items yet. A draft counts nowhere
// until it is saved (D-049); closing the browser loses nothing.

const READING_STATE: Record<Draft["ocr_status"], string> = {
  none: "not read",
  pending: "reading the photo…",
  done: "read",
  failed: "could not be read",
};

export function AddQueue() {
  usePageTitle("To review");
  const drafts = useDrafts();
  const list = drafts.data?.items ?? [];
  const first = list[0];

  return (
    <div className="queue">
      <div className="page-head">
        <h1 className="page-title">To review</h1>
        <div className="page-head__actions">
          {first ? <LinkButton to={`/add/${first.id}`}>Review next</LinkButton> : null}
          <LinkButton variant="secondary" to="/camera?mode=add">
            Open the camera
          </LinkButton>
        </div>
      </div>
      <GlassCard>
        {drafts.isPending ? (
          <div className="stack" aria-busy="true">
            <Skeleton height={72} />
            <Skeleton height={72} />
          </div>
        ) : drafts.isError ? (
          <ErrorState message={drafts.error.message} onRetry={() => void drafts.refetch()} />
        ) : list.length === 0 ? (
          <div className="empty-state">
            <p>Nothing waiting for review.</p>
            <LinkButton to="/camera?mode=add">Add an item</LinkButton>
          </div>
        ) : (
          <ul className="row-list">
            {list.map((draft) => (
              <DraftRow key={draft.id} draft={draft} />
            ))}
          </ul>
        )}
      </GlassCard>
    </div>
  );
}

function DraftRow({ draft }: { draft: Draft }) {
  const refresh = useRefreshInventory();
  const timeZone = useProfile().data?.timezone ?? "UTC";
  const [busy, setBusy] = useState(false);
  const [failure, setFailure] = useState<string | null>(null);
  const photo = draft.photos[0];
  // The owner's name first, then the name read from the photo, then "Untitled" (P-07).
  const name =
    draft.fields.name?.trim() || String(draft.proposed["name"]?.value ?? "") || "Untitled";

  async function discard() {
    if (busy) return;
    setBusy(true);
    try {
      await api.discardDraft(draft.id);
      await refresh();
    } catch (error) {
      setFailure(error instanceof Error ? error.message : "Something went wrong.");
      setBusy(false);
    }
  }

  return (
    <li className="row-list__row">
      {photo ? <img className="row-list__thumb" src={fileUrl.thumb(photo.id)} alt="" /> : null}
      <div className="row-list__text">
        <Link to={`/add/${draft.id}`}>{name}</Link>
        <span className="section-note">
          Added {formatMoment(draft.created_at, timeZone)} · {READING_STATE[draft.ocr_status]}
        </span>
        {failure ? (
          <span role="alert" className="field__error">
            {failure}
          </span>
        ) : null}
      </div>
      <LinkButton variant="secondary" to={`/add/${draft.id}`}>
        Review
      </LinkButton>
      <Button variant="ghost" loading={busy} onClick={() => void discard()}>
        Discard
      </Button>
    </li>
  );
}
