import { useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api/endpoints";
import type { ItemSummary } from "../api/endpoints";
import {
  useBackups,
  useItemList,
  useMakeBackup,
  useProfile,
  useRefreshInventory,
} from "../api/queries";
import { usePageTitle } from "../hooks/usePageTitle";
import { formatMoment } from "../lib/format";
import { splitProblems } from "../lib/formErrors";
import { ErrorState } from "../patterns/ErrorState";
import { ItemPhoto } from "../patterns/ItemVisuals";
import { Button } from "../primitives/Button";
import { GlassCard } from "../primitives/Glass";
import { Input } from "../primitives/Input";
import { Dialog } from "../primitives/Overlay";
import { Skeleton } from "../primitives/Skeleton";
import { useToast } from "../primitives/Toast";

// P-09, Trash: deleted items, which can be restored. Deleting one for good needs the typed word
// DELETE and a good backup from the last 24 hours, so the backup can still bring it back.

const DAY_MS = 24 * 60 * 60 * 1000;

export function Trash() {
  usePageTitle("Trash");
  const list = useItemList({ deleted: "only", state: "all" });
  const items = list.data?.pages.flatMap((page) => page.items) ?? [];
  const [purging, setPurging] = useState<ItemSummary | null>(null);

  return (
    <div className="trash">
      <h1 className="page-title">Trash</h1>
      <GlassCard>
        {list.isPending ? (
          <div className="stack" aria-busy="true">
            <Skeleton height={64} />
            <Skeleton height={64} />
          </div>
        ) : list.isError ? (
          <ErrorState message={list.error.message} onRetry={() => void list.refetch()} />
        ) : items.length === 0 ? (
          <div className="empty-state">
            <p>Trash is empty.</p>
          </div>
        ) : (
          <>
            <ul className="row-list">
              {items.map((item) => (
                <TrashRow key={item.public_id} item={item} onPurge={() => setPurging(item)} />
              ))}
            </ul>
            {list.hasNextPage ? (
              <Button
                variant="secondary"
                loading={list.isFetchingNextPage}
                onClick={() => void list.fetchNextPage()}
              >
                Show more
              </Button>
            ) : null}
          </>
        )}
      </GlassCard>
      {purging ? <PurgeDialog item={purging} onClose={() => setPurging(null)} /> : null}
    </div>
  );
}

function TrashRow({ item, onPurge }: { item: ItemSummary; onPurge: () => void }) {
  const refresh = useRefreshInventory();
  const toast = useToast();
  const timeZone = useProfile().data?.timezone ?? "UTC";
  const [busy, setBusy] = useState(false);
  const [failure, setFailure] = useState<string | null>(null);

  async function restore() {
    if (busy) return;
    setBusy(true);
    try {
      await api.restoreItem(item.public_id);
      await refresh();
      toast({ message: `${item.name} restored.` });
    } catch (error) {
      setFailure(error instanceof Error ? error.message : "Something went wrong.");
      setBusy(false);
    }
  }

  return (
    <li className="row-list__row">
      <ItemPhoto photoId={item.primary_photo_id} name={item.name} className="row-list__thumb" />
      <div className="row-list__text">
        <Link to={`/items/${item.public_id}`}>{item.name}</Link>
        {item.deleted_at ? (
          <span className="section-note">
            Moved to Trash {formatMoment(item.deleted_at, timeZone)}
          </span>
        ) : null}
        {failure ? (
          <span role="alert" className="field__error">
            {failure}
          </span>
        ) : null}
      </div>
      <Button variant="secondary" loading={busy} onClick={() => void restore()}>
        Restore
      </Button>
      <Button variant="ghost" onClick={onPurge}>
        Delete permanently
      </Button>
    </li>
  );
}

function PurgeDialog({ item, onClose }: { item: ItemSummary; onClose: () => void }) {
  const backups = useBackups();
  const makeBackup = useMakeBackup();
  const refresh = useRefreshInventory();
  const toast = useToast();
  const [typed, setTyped] = useState("");
  const [busy, setBusy] = useState(false);
  const [failure, setFailure] = useState<string | null>(null);

  const lastGood = backups.data?.last_good?.at;
  const recentBackup = lastGood !== undefined && Date.now() - new Date(lastGood).getTime() < DAY_MS;
  const folderMissing = backups.data?.status === "unavailable";

  async function purge() {
    if (busy) return;
    setBusy(true);
    setFailure(null);
    try {
      await api.purgeItem(item.public_id);
      await refresh();
      toast({ message: `${item.name} was deleted permanently.` });
      onClose();
    } catch (error) {
      setFailure(splitProblems(error, []).general);
      await backups.refetch();
    } finally {
      setBusy(false);
    }
  }

  return (
    <Dialog open onClose={onClose} title="Delete permanently?">
      <div className="stack">
        <p>
          {item.name} will be removed from Enderchest for good. Older backups still contain it, and
          its photo files stay on disk.
        </p>
        {recentBackup ? null : folderMissing ? (
          <p className="form-failure">
            The backup folder is not connected, so nothing can be deleted permanently. Connect it
            and restart Enderchest.
          </p>
        ) : (
          <div className="stack">
            <p>Make a backup first: permanent delete needs a good backup from the last 24 hours.</p>
            <Button
              variant="secondary"
              loading={makeBackup.isPending}
              onClick={() =>
                makeBackup.mutate(undefined, {
                  onError: (error) => setFailure(error.message),
                })
              }
            >
              Back up now
            </Button>
          </div>
        )}
        <Input
          label="Type DELETE to confirm"
          value={typed}
          autoComplete="off"
          onChange={(event) => setTyped(event.target.value)}
        />
        {failure ? (
          <p role="alert" className="form-failure">
            {failure}
          </p>
        ) : null}
        <div className="sheet-actions">
          {typed !== "DELETE" ? (
            <Button disabled disabledReason="Type DELETE in capitals first.">
              Delete permanently
            </Button>
          ) : !recentBackup ? (
            <Button disabled disabledReason="Make a backup first.">
              Delete permanently
            </Button>
          ) : (
            <Button loading={busy} onClick={() => void purge()}>
              Delete permanently
            </Button>
          )}
          <Button variant="ghost" onClick={onClose}>
            Cancel
          </Button>
        </div>
      </div>
    </Dialog>
  );
}
