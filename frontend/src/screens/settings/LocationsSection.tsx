import { useEffect, useRef, useState } from "react";
import { ApiError } from "../../api/client";
import { api } from "../../api/endpoints";
import type { Location } from "../../api/endpoints";
import { useLocations, useRefreshInventory } from "../../api/queries";
import { splitProblems } from "../../lib/formErrors";
import { ErrorState } from "../../patterns/ErrorState";
import { locationLabel } from "../../patterns/ItemFields";
import { Button } from "../../primitives/Button";
import { GlassCard } from "../../primitives/Glass";
import { Input, Select } from "../../primitives/Input";
import { Dialog } from "../../primitives/Overlay";
import { Skeleton } from "../../primitives/Skeleton";
import { AddByName, ReassignDialog } from "./CategoriesSection";

// Settings, Locations (PAGES.md P-02): an indented tree with item counts. Add a place inside
// another, rename, move (a move into itself is refused as a cycle), delete with reassign.

export function LocationsSection() {
  const locations = useLocations();
  return (
    <GlassCard title="Locations">
      <div className="stack">
        <p className="section-note">Places nest up to 5 deep: Garage › Shelf 2 › Blue box.</p>
        <AddByName label="New place" onAdd={(name) => api.createLocation({ name })} />
        {locations.isPending ? (
          <Skeleton height={48} />
        ) : locations.isError ? (
          <ErrorState message={locations.error.message} onRetry={() => void locations.refetch()} />
        ) : locations.data.length === 0 ? (
          <p className="section-note">No places yet. Add one above.</p>
        ) : (
          <ul className="row-list">
            {locations.data.map((location) => (
              <LocationRow key={location.id} location={location} all={locations.data} />
            ))}
          </ul>
        )}
      </div>
    </GlassCard>
  );
}

type Mode = "idle" | "rename" | "child" | "move";

function LocationRow({ location, all }: { location: Location; all: Location[] }) {
  const refresh = useRefreshInventory();
  const [mode, setMode] = useState<Mode>("idle");
  const [text, setText] = useState("");
  const [parent, setParent] = useState("");
  const [problem, setProblem] = useState<string | null>(null);
  const [reassign, setReassign] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const opener = useRef<HTMLButtonElement | null>(null);
  const lastMode = useRef<Mode>("idle");

  // The form goes away when it closes: put the focus back on the button that opened it. A row's
  // old message goes when its list changes too, for example when a child that was in the way goes.
  useEffect(() => {
    if (lastMode.current !== "idle" && mode === "idle") opener.current?.focus();
    lastMode.current = mode;
  }, [mode]);
  useEffect(() => setProblem(null), [all]);

  function enter(next: Mode, button: EventTarget) {
    opener.current = button as HTMLButtonElement;
    setProblem(null);
    setMode(next);
  }

  function leave() {
    setProblem(null);
    setMode("idle");
  }

  async function run(work: () => Promise<unknown>) {
    if (busy) return;
    setBusy(true);
    setProblem(null);
    try {
      await work();
      await refresh();
      setMode("idle");
    } catch (error) {
      if (
        error instanceof ApiError &&
        error.code === "in_use" &&
        error.details["reason"] === "has_items"
      ) {
        setReassign(error.message);
      } else {
        const found = splitProblems(error, ["name"]);
        setProblem(found.fields["name"] ?? found.general);
      }
    } finally {
      setBusy(false);
    }
  }

  const depth = location.path.length - 1;
  return (
    <li
      className="row-list__row row-list__row--stacked"
      style={{ paddingInlineStart: `${depth * 24}px` }}
    >
      <div className="row-list__line">
        <span className="row-list__text">
          <strong>{location.name}</strong>
          <span className="section-note">
            {location.item_count === 1 ? "1 item" : `${location.item_count} items`}
          </span>
        </span>
        <Button
          variant="ghost"
          onClick={(event) => {
            enter("child", event.currentTarget);
            setText("");
          }}
        >
          Add inside
        </Button>
        <Button
          variant="ghost"
          onClick={(event) => {
            enter("rename", event.currentTarget);
            setText(location.name);
          }}
        >
          Rename
        </Button>
        <Button
          variant="ghost"
          onClick={(event) => {
            enter("move", event.currentTarget);
            setParent(String(location.parent_id ?? ""));
          }}
        >
          Move
        </Button>
        <Button
          variant="ghost"
          loading={busy && mode === "idle"}
          onClick={() => void run(() => api.deleteLocation(location.id))}
        >
          Delete
        </Button>
      </div>
      {mode === "rename" || mode === "child" ? (
        <form
          className="inline-add"
          onSubmit={(event) => {
            event.preventDefault();
            void run(() =>
              mode === "rename"
                ? api.changeLocation(location.id, { name: text })
                : api.createLocation({ name: text, parent_id: location.id }),
            );
          }}
          onKeyDown={(event) => {
            if (event.key === "Escape") leave();
          }}
        >
          <Input
            label={mode === "rename" ? "Name" : `New place inside ${location.name}`}
            value={text}
            autoFocus
            onChange={(event) => {
              setText(event.target.value);
              setProblem(null);
            }}
          />
          {text.trim() === "" ? (
            <Button type="submit" disabled disabledReason="Type a name first.">
              Save
            </Button>
          ) : (
            <Button type="submit" loading={busy}>
              Save
            </Button>
          )}
          <Button variant="ghost" onClick={leave}>
            Cancel
          </Button>
        </form>
      ) : null}
      {problem && mode !== "move" ? (
        <p role="alert" className="field__error">
          {problem}
        </p>
      ) : null}
      <Dialog open={mode === "move"} onClose={leave} title={`Move ${location.name}`}>
        <div className="stack">
          <Select
            label="Put it inside"
            value={parent}
            onChange={(event) => setParent(event.target.value)}
            options={[
              { value: "", label: "Nothing (a top-level place)" },
              ...all
                .filter((l) => l.id !== location.id)
                .map((l) => ({ value: String(l.id), label: locationLabel(l) })),
            ]}
          />
          {problem ? (
            <p role="alert" className="form-failure">
              {problem}
            </p>
          ) : null}
          <Button
            loading={busy}
            onClick={() =>
              void run(() =>
                api.changeLocation(location.id, {
                  parent_id: parent === "" ? null : Number(parent),
                }),
              )
            }
          >
            Move
          </Button>
        </div>
      </Dialog>
      {reassign ? (
        <ReassignDialog
          title={`Delete ${location.name}`}
          message={reassign}
          noneLabel="No location"
          options={all
            .filter((l) => l.id !== location.id)
            .map((l) => ({ value: String(l.id), label: locationLabel(l) }))}
          onClose={() => setReassign(null)}
          onConfirm={(target) =>
            run(() => api.deleteLocation(location.id, target)).then(() => setReassign(null))
          }
        />
      ) : null}
    </li>
  );
}
