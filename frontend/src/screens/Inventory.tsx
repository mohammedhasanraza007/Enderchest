import { useEffect, useMemo, useRef, useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { useWindowVirtualizer } from "@tanstack/react-virtual";
import { Search } from "lucide-react";
import { api } from "../api/endpoints";
import type { ItemFilters, ItemSummary } from "../api/endpoints";
import {
  useCategories,
  useDrafts,
  useItemList,
  useLocations,
  useRefreshInventory,
} from "../api/queries";
import { usePageTitle } from "../hooks/usePageTitle";
import { filtersFromQuery, isFiltered, queryFromFilters } from "../lib/inventoryQuery";
import { ErrorState } from "../patterns/ErrorState";
import { locationLabel } from "../patterns/ItemFields";
import { ExpiryChip, ItemPhoto, StateChip } from "../patterns/ItemVisuals";
import { OverflowMenu } from "../patterns/OverflowMenu";
import { Button, LinkButton } from "../primitives/Button";
import { GlassCard } from "../primitives/Glass";
import { Select } from "../primitives/Input";
import { Dialog } from "../primitives/Overlay";
import { Skeleton } from "../primitives/Skeleton";
import { useToast } from "../primitives/Toast";

// P-03, Inventory. The filters live in the URL so Back restores them. The grid is virtualised:
// only the rows on screen exist in the page, so 1,000 items scroll smoothly (PAGES.md P-03).

const ROW_HEIGHT = 292;

function columnsFor(width: number): number {
  if (width >= 1100) return 4;
  if (width >= 760) return 3;
  return 2;
}

export function Inventory() {
  usePageTitle("Inventory");
  const [query, setQuery] = useSearchParams();
  const filters = useMemo(() => filtersFromQuery(query), [query]);
  const list = useItemList(filters);
  const drafts = useDrafts();
  const [selecting, setSelecting] = useState(false);
  const [selected, setSelected] = useState<Set<string>>(new Set());

  const items = useMemo(() => list.data?.pages.flatMap((page) => page.items) ?? [], [list.data]);
  const total = list.data?.pages[0]?.total;
  const waiting = drafts.data?.items.length ?? 0;

  function update(next: ItemFilters) {
    setQuery(queryFromFilters(next), { replace: true });
  }

  function toggle(publicId: string) {
    const next = new Set(selected);
    if (next.has(publicId)) next.delete(publicId);
    else next.add(publicId);
    setSelected(next);
  }

  return (
    <div className="inventory">
      <div className="page-head">
        <h1 className="page-title">Inventory</h1>
        <div className="page-head__actions">
          {waiting > 0 ? (
            <LinkButton variant="secondary" to="/add">
              To review ({waiting})
            </LinkButton>
          ) : null}
          <Button
            variant="secondary"
            aria-pressed={selecting}
            onClick={() => {
              setSelecting((value) => !value);
              setSelected(new Set());
            }}
          >
            {selecting ? "Done selecting" : "Print labels"}
          </Button>
          <LinkButton to="/camera?mode=add">＋ Add item</LinkButton>
          <OverflowMenu
            label="More inventory actions"
            actions={[{ label: "Trash", to: "/trash" }]}
          />
        </div>
      </div>

      <Filters filters={filters} onChange={update} />

      {selecting ? (
        <SelectionBar
          selected={items.filter((item) => selected.has(item.public_id))}
          onDone={() => setSelected(new Set())}
        />
      ) : null}

      {list.isPending ? (
        <div className="item-grid item-grid--static" aria-busy="true">
          {Array.from({ length: 8 }, (_, index) => (
            <div className="item-tile" key={index}>
              <Skeleton height={170} />
              <Skeleton width="70%" />
              <Skeleton width="40%" />
            </div>
          ))}
        </div>
      ) : list.isError ? (
        <GlassCard>
          <ErrorState message={list.error.message} onRetry={() => void list.refetch()} />
        </GlassCard>
      ) : items.length === 0 ? (
        <GlassCard className="empty-state">
          {isFiltered(filters) ? (
            <>
              <p>Nothing matches these filters.</p>
              <Button variant="secondary" onClick={() => update({ sort: filters.sort })}>
                Clear filters
              </Button>
            </>
          ) : (
            <>
              <p>No items yet.</p>
              <LinkButton to="/camera?mode=add">Add item</LinkButton>
            </>
          )}
        </GlassCard>
      ) : (
        <>
          <p className="inventory__count" aria-live="polite">
            {total === 1 ? "1 item" : `${total ?? items.length} items`}
          </p>
          <ItemGrid
            items={items}
            selecting={selecting}
            selected={selected}
            onToggle={toggle}
            hasMore={list.hasNextPage}
            loadMore={() => {
              if (!list.isFetchingNextPage) void list.fetchNextPage();
            }}
          />
        </>
      )}
    </div>
  );
}

function Filters({
  filters,
  onChange,
}: {
  filters: ItemFilters;
  onChange: (f: ItemFilters) => void;
}) {
  const categories = useCategories();
  const locations = useLocations();
  const [text, setText] = useState(filters.q ?? "");
  const latest = useRef({ filters, onChange });
  latest.current = { filters, onChange };

  // Clear filters (or Back) changes the query: the search box follows it.
  useEffect(() => setText(filters.q ?? ""), [filters.q]);

  // Typing waits a moment before searching, so each key press is not a request.
  useEffect(() => {
    const timer = window.setTimeout(() => {
      const { filters: current, onChange: apply } = latest.current;
      if ((current.q ?? "") !== text) apply({ ...current, q: text });
    }, 300);
    return () => window.clearTimeout(timer);
  }, [text]);

  const value = (n: number | undefined) => (n === undefined ? "" : String(n));
  const number = (s: string) => (s === "" ? undefined : Number(s));
  return (
    <div className="filters" role="search">
      <label className="search-pill">
        <Search size={18} strokeWidth={1.5} aria-hidden="true" />
        <input
          type="search"
          aria-label="Search items"
          value={text}
          placeholder="Search by name, size, model or ID"
          onChange={(event) => setText(event.target.value)}
        />
      </label>
      <Select
        label="Category"
        value={value(filters.category_id ?? undefined)}
        onChange={(event) => onChange({ ...filters, category_id: number(event.target.value) })}
        options={[
          { value: "", label: "All" },
          ...(categories.data ?? []).map((c) => ({ value: String(c.id), label: c.name })),
        ]}
      />
      <Select
        label="Location"
        value={value(filters.location_id ?? undefined)}
        onChange={(event) => onChange({ ...filters, location_id: number(event.target.value) })}
        options={[
          { value: "", label: "All" },
          ...(locations.data ?? []).map((l) => ({ value: String(l.id), label: locationLabel(l) })),
        ]}
      />
      <Select
        label="State"
        value={filters.state ?? "active"}
        onChange={(event) =>
          onChange({ ...filters, state: event.target.value as ItemFilters["state"] })
        }
        options={[
          { value: "active", label: "Active" },
          { value: "used", label: "Used" },
          { value: "expired", label: "Marked expired" },
          { value: "discarded", label: "Discarded" },
          { value: "all", label: "All" },
        ]}
      />
      <Select
        label="Expiry"
        value={filters.expiry ?? "any"}
        onChange={(event) =>
          onChange({ ...filters, expiry: event.target.value as ItemFilters["expiry"] })
        }
        options={[
          { value: "any", label: "Any" },
          { value: "soon", label: "Expires soon" },
          { value: "today", label: "Expires today" },
          { value: "past", label: "Expired" },
          { value: "none", label: "No expiry" },
          { value: "unknown", label: "Date not set" },
        ]}
      />
      <Select
        label="Photo"
        value={
          filters.has_photo === undefined || filters.has_photo === null
            ? ""
            : filters.has_photo
              ? "yes"
              : "no"
        }
        onChange={(event) =>
          onChange({
            ...filters,
            has_photo: event.target.value === "" ? undefined : event.target.value === "yes",
          })
        }
        options={[
          { value: "", label: "Any" },
          { value: "yes", label: "With photo" },
          { value: "no", label: "Without photo" },
        ]}
      />
      <Select
        label="Sort"
        value={filters.sort ?? "created_desc"}
        onChange={(event) =>
          onChange({ ...filters, sort: event.target.value as ItemFilters["sort"] })
        }
        options={[
          { value: "created_desc", label: "Newest first" },
          { value: "name_asc", label: "Name A to Z" },
          { value: "expiry_asc", label: "Expiry soonest" },
        ]}
      />
    </div>
  );
}

interface GridProps {
  items: ItemSummary[];
  selecting: boolean;
  selected: Set<string>;
  onToggle: (publicId: string) => void;
  hasMore: boolean;
  loadMore: () => void;
}

function ItemGrid({ items, selecting, selected, onToggle, hasMore, loadMore }: GridProps) {
  const container = useRef<HTMLDivElement>(null);
  const [columns, setColumns] = useState(4);
  const [offset, setOffset] = useState(0);

  useEffect(() => {
    const element = container.current;
    if (!element) return;
    const observer = new ResizeObserver(() => {
      setColumns(columnsFor(element.clientWidth));
      setOffset(element.getBoundingClientRect().top + window.scrollY);
    });
    observer.observe(element);
    return () => observer.disconnect();
  }, []);

  const rows = Math.ceil(items.length / columns);
  const virtualizer = useWindowVirtualizer({
    count: rows,
    estimateSize: () => ROW_HEIGHT,
    overscan: 3,
    scrollMargin: offset,
  });
  const visible = virtualizer.getVirtualItems();
  const lastRow = visible[visible.length - 1]?.index ?? 0;

  // Near the end of what is loaded, fetch the next page (infinite scroll, PAGES.md P-03).
  useEffect(() => {
    if (hasMore && lastRow >= rows - 3) loadMore();
  }, [hasMore, lastRow, rows, loadMore]);

  return (
    <div ref={container} className="item-grid" style={{ height: virtualizer.getTotalSize() }}>
      {visible.map((row) => (
        <div
          key={row.key}
          className="item-grid__row"
          style={{
            transform: `translateY(${row.start - virtualizer.options.scrollMargin}px)`,
            gridTemplateColumns: `repeat(${columns}, minmax(0, 1fr))`,
          }}
        >
          {items.slice(row.index * columns, row.index * columns + columns).map((item) => (
            <ItemTile
              key={item.public_id}
              item={item}
              selecting={selecting}
              checked={selected.has(item.public_id)}
              onToggle={() => onToggle(item.public_id)}
            />
          ))}
        </div>
      ))}
    </div>
  );
}

function ItemTile({
  item,
  selecting,
  checked,
  onToggle,
}: {
  item: ItemSummary;
  selecting: boolean;
  checked: boolean;
  onToggle: () => void;
}) {
  const where = [item.category_name, item.location_path.join(" › ")].filter(Boolean).join(" · ");
  const body = (
    <>
      <ItemPhoto photoId={item.primary_photo_id} name={item.name} className="item-tile__photo" />
      <span className="item-tile__name">{item.name}</span>
      <span className="item-tile__where">{where || "No category or location"}</span>
      <span className="item-tile__chips">
        {item.quantity > 1 ? <span className="chip">×{item.quantity}</span> : null}
        <ExpiryChip expiry={item.expiry} />
        <StateChip state={item.state} />
      </span>
    </>
  );
  if (selecting) {
    return (
      <label className={["item-tile", checked ? "is-selected" : ""].filter(Boolean).join(" ")}>
        <input type="checkbox" className="item-tile__check" checked={checked} onChange={onToggle} />
        <span className="visually-hidden">Select {item.name}</span>
        {body}
      </label>
    );
  }
  return (
    <Link className="item-tile" to={`/items/${item.public_id}`}>
      {body}
    </Link>
  );
}

/** Select mode's bar: print labels, move, or delete the chosen items (PAGES.md P-03). */
function SelectionBar({ selected, onDone }: { selected: ItemSummary[]; onDone: () => void }) {
  const navigate = useNavigate();
  const locations = useLocations();
  const refresh = useRefreshInventory();
  const toast = useToast();
  const [moving, setMoving] = useState(false);
  const [target, setTarget] = useState("");
  const [busy, setBusy] = useState(false);
  const [failure, setFailure] = useState<string | null>(null);
  const ids = selected.map((item) => item.public_id);
  const none = ids.length === 0;
  const reason = "Choose items first.";

  async function run(work: () => Promise<void>) {
    if (busy) return;
    setBusy(true);
    setFailure(null);
    try {
      await work();
    } catch (error) {
      setFailure(error instanceof Error ? error.message : "Something went wrong.");
    } finally {
      await refresh();
      setBusy(false);
    }
  }

  const remove = () =>
    run(async () => {
      const events: number[] = [];
      for (const id of ids) events.push((await api.deleteItem(id)).event_id);
      onDone();
      toast({
        message:
          events.length === 1 ? "1 item moved to Trash." : `${events.length} items moved to Trash.`,
        actionLabel: "Undo",
        onAction: () => {
          void Promise.all(events.map((event) => api.undo(event))).then(refresh);
        },
      });
    });

  const move = () =>
    run(async () => {
      const locationId = target === "" ? null : Number(target);
      for (const id of ids) await api.changeItem(id, { location_id: locationId });
      setMoving(false);
      onDone();
      toast({ message: ids.length === 1 ? "1 item moved." : `${ids.length} items moved.` });
    });

  return (
    <div className="selection-bar" role="region" aria-label="Selected items">
      <span>{none ? "No items chosen" : `${ids.length} chosen`}</span>
      {none ? (
        <>
          <Button disabled disabledReason={reason}>
            Print labels
          </Button>
          <Button variant="secondary" disabled disabledReason={reason}>
            Move to location
          </Button>
          <Button variant="secondary" disabled disabledReason={reason}>
            Delete
          </Button>
        </>
      ) : (
        <>
          <Button onClick={() => navigate(`/labels?ids=${ids.join(",")}`)}>Print labels</Button>
          <Button variant="secondary" onClick={() => setMoving(true)}>
            Move to location
          </Button>
          <Button variant="secondary" loading={busy} onClick={() => void remove()}>
            Delete
          </Button>
        </>
      )}
      {failure ? (
        <p role="alert" className="form-failure">
          {failure}
        </p>
      ) : null}
      <Dialog open={moving} onClose={() => setMoving(false)} title="Move to location">
        <div className="stack">
          <Select
            label="Location"
            value={target}
            onChange={(event) => setTarget(event.target.value)}
            options={[
              { value: "", label: "No location" },
              ...(locations.data ?? []).map((l) => ({
                value: String(l.id),
                label: locationLabel(l),
              })),
            ]}
          />
          <Button loading={busy} onClick={() => void move()}>
            Move {ids.length === 1 ? "1 item" : `${ids.length} items`}
          </Button>
        </div>
      </Dialog>
    </div>
  );
}
