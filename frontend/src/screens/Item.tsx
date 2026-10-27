import { useRef, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { ChevronLeft, ChevronRight, Star, Trash2 } from "lucide-react";
import { ApiError } from "../api/client";
import { api, fileUrl } from "../api/endpoints";
import type { EventView, ItemDetail } from "../api/endpoints";
import { useItem, useItemEvents, useProfile, useRefreshInventory } from "../api/queries";
import { usePageTitle } from "../hooks/usePageTitle";
import { formatDay, formatMoment } from "../lib/format";
import { valuesFromItem } from "../lib/itemForm";
import { formatRupees } from "../lib/money";
import { ErrorState } from "../patterns/ErrorState";
import { ItemFormSheet } from "../patterns/ItemFormSheet";
import { ExpiryChip, ItemPhoto, StateChip } from "../patterns/ItemVisuals";
import { MaintenanceCard } from "../patterns/MaintenanceCard";
import { OverflowMenu } from "../patterns/OverflowMenu";
import { Button, LinkButton } from "../primitives/Button";
import { GlassCard, InnerPanel } from "../primitives/Glass";
import { Skeleton } from "../primitives/Skeleton";
import { useToast } from "../primitives/Toast";
import { NotFound } from "./NotFound";

// P-04, the item page: photos, the details card, the label card, the maintenance card and the
// history. An active item can be used, marked expired or discarded (each with Undo); an item that
// is not active says so and offers Reactivate (Phase 4).

export function Item() {
  const { publicId = "" } = useParams();
  const item = useItem(publicId);
  usePageTitle(item.data?.name ?? "Item");

  if (item.isPending) {
    return (
      <div className="item-page" aria-busy="true">
        <Skeleton height={420} />
        <GlassCard>
          <div className="stack">
            <Skeleton width="60%" height={32} />
            <Skeleton />
            <Skeleton width="40%" />
          </div>
        </GlassCard>
      </div>
    );
  }
  if (item.isError) {
    if (item.error instanceof ApiError && item.error.code === "not_found") {
      return <NotFound title="That item doesn't exist" />;
    }
    return (
      <GlassCard>
        <ErrorState message={item.error.message} onRetry={() => void item.refetch()} />
      </GlassCard>
    );
  }
  return <ItemView item={item.data} />;
}

function ItemView({ item }: { item: ItemDetail }) {
  const navigate = useNavigate();
  const refresh = useRefreshInventory();
  const toast = useToast();
  const timeZone = useProfile().data?.timezone ?? "UTC";
  const [editing, setEditing] = useState(false);
  const [duplicating, setDuplicating] = useState(false);
  const [busy, setBusy] = useState(false);
  const [failure, setFailure] = useState<string | null>(null);

  async function remove() {
    if (busy) return;
    setBusy(true);
    try {
      const { event_id } = await api.deleteItem(item.public_id);
      await refresh();
      toast({
        message: "Moved to Trash.",
        actionLabel: "Undo",
        onAction: () => void api.undo(event_id).then(refresh),
      });
      navigate("/inventory");
    } catch (error) {
      setFailure(error instanceof Error ? error.message : "Something went wrong.");
    } finally {
      setBusy(false);
    }
  }

  async function restore() {
    if (busy) return;
    setBusy(true);
    try {
      await api.restoreItem(item.public_id);
      await refresh();
      toast({ message: "Restored from Trash." });
    } catch (error) {
      setFailure(error instanceof Error ? error.message : "Something went wrong.");
    } finally {
      setBusy(false);
    }
  }

  /** Use it, Mark expired, Discard: each answers with an event id for the 10 s Undo. */
  async function lifecycle(action: "use" | "expire" | "discard") {
    if (busy) return;
    setBusy(true);
    setFailure(null);
    try {
      const call =
        action === "use"
          ? api.markUsed(item.public_id)
          : action === "expire"
            ? api.markExpired(item.public_id)
            : api.discard(item.public_id);
      const { item: saved, event_id } = await call;
      await refresh();
      const word =
        action === "use"
          ? saved.state === "used"
            ? "Used up."
            : `Used one. ${saved.quantity} left.`
          : action === "expire"
            ? "Marked expired."
            : "Discarded.";
      toast({
        message: word,
        actionLabel: "Undo",
        onAction: () =>
          void api
            .undo(event_id)
            .then(refresh)
            .catch((error: unknown) =>
              toast({ message: error instanceof Error ? error.message : "Undo did not work." }),
            ),
      });
    } catch (error) {
      setFailure(error instanceof Error ? error.message : "Something went wrong.");
    } finally {
      setBusy(false);
    }
  }

  async function reactivate() {
    if (busy) return;
    setBusy(true);
    setFailure(null);
    try {
      await api.reactivate(item.public_id);
      await refresh();
      toast({ message: `${item.name} is active again.` });
    } catch (error) {
      setFailure(error instanceof Error ? error.message : "Something went wrong.");
    } finally {
      setBusy(false);
    }
  }

  const where = item.location_path.join(" › ");
  const active = item.state === "active" && item.deleted_at === null;
  return (
    <div className="item-page">
      {item.state !== "active" && item.deleted_at === null ? (
        <InnerPanel className="item-banner" role="status">
          <span>{STATE_BANNER[item.state]}</span>
          <Button loading={busy} onClick={() => void reactivate()}>
            Reactivate
          </Button>
        </InnerPanel>
      ) : null}
      {item.deleted_at ? (
        <InnerPanel className="item-banner" role="status">
          <span>In Trash since {formatMoment(item.deleted_at, timeZone)}.</span>
          <Button loading={busy} onClick={() => void restore()}>
            Restore
          </Button>
        </InnerPanel>
      ) : null}
      {failure ? (
        <p role="alert" className="form-failure item-page__wide">
          {failure}
        </p>
      ) : null}

      <div className="item-page__media">
        <PhotoFrame item={item} />
        {item.label.no_label_needed ? null : <LabelCard item={item} timeZone={timeZone} />}
        <MaintenanceCard item={item} />
        <History publicId={item.public_id} timeZone={timeZone} />
      </div>

      <GlassCard className="item-card">
        <div className="item-card__head">
          <h1 className="item-card__name">{item.name}</h1>
          <span className="item-card__chips">
            <ExpiryChip expiry={item.expiry} always />
            <StateChip state={item.state} />
          </span>
        </div>
        <p className="item-card__where">
          {[item.category?.name ?? "No category", where || "No location"].join(" · ")}
        </p>
        <dl className="detail-rows">
          <div>
            <dt>Quantity</dt>
            <dd>{item.quantity}</dd>
          </div>
          <div>
            <dt>Price of one</dt>
            <dd>{item.price_paise === null ? "Not set" : formatRupees(item.price_paise)}</dd>
          </div>
          <div>
            <dt>Expiry</dt>
            <dd>{item.expiry.date ? formatDay(item.expiry.date) : item.expiry.word}</dd>
          </div>
          {Object.entries(item.attributes).map(([key, value]) => (
            <div key={key}>
              <dt>{sentence(key)}</dt>
              <dd>{Array.isArray(value) ? value.join(", ") : value}</dd>
            </div>
          ))}
        </dl>
        {item.notes ? <p className="item-card__notes">{item.notes}</p> : null}
        {active || !item.deleted_at ? (
          // One wrapping row (Phase 8 polish): the lifecycle actions, then Edit and More.
          <div className="item-card__actions">
            {active ? (
              <>
                <Button loading={busy} onClick={() => void lifecycle("use")}>
                  Use it
                </Button>
                <Button variant="secondary" onClick={() => void lifecycle("expire")}>
                  Mark expired
                </Button>
                <Button variant="secondary" onClick={() => void lifecycle("discard")}>
                  Discard
                </Button>
              </>
            ) : null}
            {item.deleted_at ? null : (
              <>
                {/* Beside Use it, Edit steps back so the card has one main action. */}
                <Button variant={active ? "secondary" : "primary"} onClick={() => setEditing(true)}>
                  Edit
                </Button>
                <OverflowMenu
                  label="More item actions"
                  actions={[
                    { label: "Duplicate", onSelect: () => setDuplicating(true) },
                    { label: "Delete", onSelect: () => void remove() },
                  ]}
                />
              </>
            )}
          </div>
        ) : null}
      </GlassCard>

      <ItemFormSheet
        open={editing}
        onClose={() => setEditing(false)}
        editing={item}
        initial={valuesFromItem(item)}
        onSaved={() => undefined}
      />
      <ItemFormSheet
        open={duplicating}
        onClose={() => setDuplicating(false)}
        initial={{ ...valuesFromItem(item), name: `${item.name} (copy)` }}
        onSaved={(made) => navigate(`/items/${made.public_id}`)}
      />
    </div>
  );
}

/** The photo frame with ‹ ›, Add photo, ★ primary and hide, then the thumbnail strip. */
function PhotoFrame({ item }: { item: ItemDetail }) {
  const refresh = useRefreshInventory();
  const toast = useToast();
  const picker = useRef<HTMLInputElement>(null);
  const [index, setIndex] = useState(0);
  const [busy, setBusy] = useState(false);
  const [failure, setFailure] = useState<string | null>(null);
  const photos = item.photos;
  const current = photos[Math.min(index, photos.length - 1)];
  const canAdd = photos.length < 12 && item.deleted_at === null;

  async function act(work: () => Promise<unknown>, done?: string) {
    if (busy) return;
    setBusy(true);
    setFailure(null);
    try {
      await work();
      await refresh();
      if (done) toast({ message: done });
    } catch (error) {
      setFailure(error instanceof Error ? error.message : "Something went wrong.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="photo-frame">
      <div className="photo-frame__main">
        <ItemPhoto
          photoId={current?.id ?? null}
          name={item.name}
          size="file"
          className="photo-frame__image"
        />
        {photos.length > 1 ? (
          <>
            <button
              type="button"
              className="photo-frame__nav photo-frame__nav--prev"
              aria-label="Previous photo"
              onClick={() => setIndex((index - 1 + photos.length) % photos.length)}
            >
              <ChevronLeft size={22} strokeWidth={1.5} aria-hidden="true" />
            </button>
            <button
              type="button"
              className="photo-frame__nav photo-frame__nav--next"
              aria-label="Next photo"
              onClick={() => setIndex((index + 1) % photos.length)}
            >
              <ChevronRight size={22} strokeWidth={1.5} aria-hidden="true" />
            </button>
          </>
        ) : null}
      </div>
      <div className="photo-frame__actions">
        <input
          ref={picker}
          type="file"
          accept="image/jpeg,image/png,image/webp"
          hidden
          onChange={(event) => {
            const file = event.target.files?.[0];
            event.target.value = "";
            if (file) {
              void act(async () => {
                await api.addPhoto(item.public_id, file);
                setIndex(photos.length);
              }, "Photo added.");
            }
          }}
        />
        {canAdd ? (
          <Button variant="secondary" loading={busy} onClick={() => picker.current?.click()}>
            Add photo
          </Button>
        ) : (
          <Button
            variant="secondary"
            disabled
            disabledReason={item.deleted_at ? "Restore the item first." : "12 photos is the most."}
          >
            Add photo
          </Button>
        )}
        {current && item.deleted_at === null ? (
          <>
            {current.is_primary ? (
              <span className="chip photo-frame__main-label">
                <Star size={16} strokeWidth={1.5} aria-hidden="true" /> Main photo
              </span>
            ) : (
              <Button
                variant="ghost"
                onClick={() => void act(() => api.setPrimaryPhoto(item.public_id, current.id))}
              >
                <Star size={18} strokeWidth={1.5} aria-hidden="true" /> Make main photo
              </Button>
            )}
            <Button
              variant="ghost"
              onClick={() =>
                void act(async () => {
                  await api.hidePhoto(current.id);
                  setIndex(0);
                }, "Photo hidden. The file is kept.")
              }
            >
              <Trash2 size={18} strokeWidth={1.5} aria-hidden="true" /> Hide photo
            </Button>
          </>
        ) : null}
      </div>
      {failure ? (
        <p role="alert" className="form-failure">
          {failure}
        </p>
      ) : null}
      {photos.length > 1 ? (
        <div className="photo-strip">
          {photos.map((photo, position) => (
            <button
              key={photo.id}
              type="button"
              className={["photo-strip__thumb", photo.id === current?.id ? "is-current" : ""]
                .filter(Boolean)
                .join(" ")}
              aria-label={`Photo ${position + 1}${photo.is_primary ? ", main photo" : ""}`}
              aria-pressed={photo.id === current?.id}
              onClick={() => setIndex(position)}
            >
              <ItemPhoto photoId={photo.id} name={item.name} />
            </button>
          ))}
        </div>
      ) : null}
    </div>
  );
}

/** The QR label: the code, the id in mono, Copy, Print label, and whether it was printed. */
function LabelCard({ item, timeZone }: { item: ItemDetail; timeZone: string }) {
  const toast = useToast();
  return (
    <GlassCard className="label-card" title="Label" headingLevel={2}>
      <div className="label-card__body">
        <img
          className="label-card__qr"
          src={fileUrl.qr(item.public_id)}
          alt={`QR code for ${item.public_id}`}
        />
        <div className="stack">
          <code className="label-card__id">{item.public_id}</code>
          <p className="section-note">
            {item.label.printed_at
              ? `Printed ${formatMoment(item.label.printed_at, timeZone)}`
              : "Not printed"}
          </p>
          <div className="chip-row">
            <Button
              variant="secondary"
              onClick={() =>
                void navigator.clipboard.writeText(item.public_id).then(
                  () => toast({ message: "ID copied." }),
                  () => toast({ message: "Copy did not work. Select the ID and copy it." }),
                )
              }
            >
              Copy
            </Button>
            <LinkButton to={`/labels?ids=${item.public_id}`}>Print label</LinkButton>
          </div>
        </div>
      </div>
    </GlassCard>
  );
}

/** "part_no" as "Part no": sentence case, the house style (DESIGN.md 12). */
function sentence(key: string): string {
  const words = key.replace(/_/g, " ");
  return words.charAt(0).toUpperCase() + words.slice(1);
}

const STATE_BANNER = {
  used: "Used up. Reactivate it if you have more.",
  expired: "Marked expired.",
  discarded: "Discarded.",
} as const;

const EVENT_WORDS: Record<string, string> = {
  item_created: "Added",
  item_updated: "Edited",
  item_deleted: "Moved to Trash",
  item_restored: "Restored from Trash",
  label_printed: "Label marked as printed",
  photo_added: "Photo added",
  photo_removed: "Photo hidden",
  draft_committed: "Saved from the camera",
  item_used: "Used",
  item_expired_marked: "Marked expired",
  item_discarded: "Discarded",
  item_reactivated: "Reactivated",
  task_created: "Maintenance plan made",
  task_updated: "Maintenance plan changed",
  task_deleted: "Maintenance plan deleted",
  task_done: "Maintenance done",
  task_skipped: "Inspection skipped",
  inspection_done: "Inspected",
  notification_resolved: "Reminder closed",
};

function eventWord(event: EventView): string {
  return EVENT_WORDS[event.kind] ?? event.kind.replace(/_/g, " ");
}

/** The item's history, newest first, a page at a time. */
function History({ publicId, timeZone }: { publicId: string; timeZone: string }) {
  const events = useItemEvents(publicId);
  const all = events.data?.pages.flatMap((page) => page.items) ?? [];
  return (
    <GlassCard title="History" headingLevel={2} className="history">
      {events.isPending ? (
        <Skeleton />
      ) : events.isError ? (
        <ErrorState message={events.error.message} onRetry={() => void events.refetch()} />
      ) : (
        <>
          {all.length === 0 ? <p className="section-note">Nothing recorded yet.</p> : null}
          <ol className="history__list">
            {all.map((event, position) => (
              <li key={`${event.at}-${position}`}>
                <span>{eventWord(event)}</span>
                <span className="section-note">{formatMoment(event.at, timeZone)}</span>
              </li>
            ))}
          </ol>
          {events.hasNextPage ? (
            <Button
              variant="secondary"
              loading={events.isFetchingNextPage}
              onClick={() => void events.fetchNextPage()}
            >
              Show older
            </Button>
          ) : null}
        </>
      )}
    </GlassCard>
  );
}
