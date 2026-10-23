import { useState } from "react";
import { ApiError } from "../../api/client";
import { api } from "../../api/endpoints";
import type { Category, CategoryPatch } from "../../api/endpoints";
import { useCategories, useRefreshInventory } from "../../api/queries";
import { splitProblems } from "../../lib/formErrors";
import { ErrorState } from "../../patterns/ErrorState";
import { Button } from "../../primitives/Button";
import { GlassCard } from "../../primitives/Glass";
import { Input, Select } from "../../primitives/Input";
import { Dialog } from "../../primitives/Overlay";
import { Skeleton } from "../../primitives/Skeleton";
import { Toggle } from "../../primitives/Toggle";

// Settings, Categories (PAGES.md P-02): the list with item counts, add, rename, the three
// defaults a new item starts with, and delete (a category still in use asks where its items go).

export function CategoriesSection() {
  const categories = useCategories();
  return (
    <GlassCard title="Categories">
      <div className="stack">
        <p className="section-note">
          A new item starts with its category's defaults. You can change them on each item.
        </p>
        <AddByName label="New category" onAdd={(name) => api.createCategory({ name })} />
        {categories.isPending ? (
          <Skeleton height={48} />
        ) : categories.isError ? (
          <ErrorState
            message={categories.error.message}
            onRetry={() => void categories.refetch()}
          />
        ) : categories.data.length === 0 ? (
          <p className="section-note">No categories yet. Add one above.</p>
        ) : (
          <ul className="row-list">
            {categories.data.map((category) => (
              <CategoryRow key={category.id} category={category} all={categories.data} />
            ))}
          </ul>
        )}
      </div>
    </GlassCard>
  );
}

/** A name field and an Add button; shared with Locations. */
export function AddByName({
  label,
  onAdd,
}: {
  label: string;
  onAdd: (name: string) => Promise<unknown>;
}) {
  const refresh = useRefreshInventory();
  const [name, setName] = useState("");
  const [problem, setProblem] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function add() {
    if (busy) return;
    setBusy(true);
    setProblem(null);
    try {
      await onAdd(name);
      await refresh();
      setName("");
    } catch (error) {
      const found = splitProblems(error, ["name"]);
      setProblem(found.fields["name"] ?? found.general);
    } finally {
      setBusy(false);
    }
  }

  return (
    <form
      className="inline-add"
      onSubmit={(event) => {
        event.preventDefault();
        if (name.trim() !== "") void add();
      }}
    >
      <Input
        label={label}
        value={name}
        onChange={(event) => setName(event.target.value)}
        error={problem ?? undefined}
      />
      {name.trim() === "" ? (
        <Button type="submit" disabled disabledReason="Type a name first.">
          Add
        </Button>
      ) : (
        <Button type="submit" loading={busy}>
          Add
        </Button>
      )}
    </form>
  );
}

function CategoryRow({ category, all }: { category: Category; all: Category[] }) {
  const refresh = useRefreshInventory();
  const [renaming, setRenaming] = useState(false);
  const [name, setName] = useState(category.name);
  const [problem, setProblem] = useState<string | null>(null);
  const [reassign, setReassign] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function change(body: CategoryPatch) {
    setProblem(null);
    try {
      await api.changeCategory(category.id, body);
      await refresh();
      setRenaming(false);
    } catch (error) {
      const found = splitProblems(error, ["name"]);
      setProblem(found.fields["name"] ?? found.general);
    }
  }

  async function remove(target?: number | "none") {
    if (busy) return;
    setBusy(true);
    setProblem(null);
    try {
      await api.deleteCategory(category.id, target);
      await refresh();
    } catch (error) {
      if (error instanceof ApiError && error.code === "in_use") {
        setReassign(error.message);
      } else {
        setProblem(splitProblems(error, []).general);
      }
    } finally {
      setBusy(false);
    }
  }

  return (
    <li className="row-list__row row-list__row--stacked">
      <div className="row-list__line">
        {renaming ? (
          <form
            className="inline-add"
            onSubmit={(event) => {
              event.preventDefault();
              void change({ name });
            }}
          >
            <Input label="Name" value={name} onChange={(event) => setName(event.target.value)} />
            <Button type="submit">Save</Button>
            <Button variant="ghost" onClick={() => setRenaming(false)}>
              Cancel
            </Button>
          </form>
        ) : (
          <>
            <span className="row-list__text">
              <strong>{category.name}</strong>
              <span className="section-note">
                {category.item_count === 1 ? "1 item" : `${category.item_count} items`}
              </span>
            </span>
            <Button variant="ghost" onClick={() => setRenaming(true)}>
              Rename
            </Button>
            <Button variant="ghost" loading={busy} onClick={() => void remove()}>
              Delete
            </Button>
          </>
        )}
      </div>
      <div className="row-list__toggles">
        <Toggle
          label="Has an expiry date"
          checked={category.expires_default}
          onChange={(next) => void change({ expires_default: next })}
        />
        <Toggle
          label="Maintenance on"
          checked={category.maintenance_default}
          onChange={(next) => void change({ maintenance_default: next })}
        />
        <Toggle
          label="Needs a printed label"
          checked={category.label_default}
          onChange={(next) => void change({ label_default: next })}
        />
      </div>
      {problem ? (
        <p role="alert" className="field__error">
          {problem}
        </p>
      ) : null}
      {reassign ? (
        <ReassignDialog
          title={`Delete ${category.name}`}
          message={reassign}
          noneLabel="No category"
          options={all
            .filter((c) => c.id !== category.id)
            .map((c) => ({ value: String(c.id), label: c.name }))}
          onClose={() => setReassign(null)}
          onConfirm={(target) => remove(target).then(() => setReassign(null))}
        />
      ) : null}
    </li>
  );
}

/** "Move its items to …" before a delete (API 2.4 `reassign_to`); shared with Locations. */
export function ReassignDialog({
  title,
  message,
  noneLabel,
  options,
  onClose,
  onConfirm,
}: {
  title: string;
  message: string;
  noneLabel: string;
  options: Array<{ value: string; label: string }>;
  onClose: () => void;
  onConfirm: (target: number | "none") => Promise<void>;
}) {
  const [target, setTarget] = useState("none");
  const [busy, setBusy] = useState(false);
  return (
    <Dialog open onClose={onClose} title={title}>
      <div className="stack">
        <p>{message}</p>
        <Select
          label="Move them to"
          value={target}
          onChange={(event) => setTarget(event.target.value)}
          options={[{ value: "none", label: noneLabel }, ...options]}
        />
        <div className="sheet-actions">
          <Button
            loading={busy}
            onClick={() => {
              setBusy(true);
              void onConfirm(target === "none" ? "none" : Number(target)).finally(() =>
                setBusy(false),
              );
            }}
          >
            Move and delete
          </Button>
          <Button variant="ghost" onClick={onClose}>
            Cancel
          </Button>
        </div>
      </div>
    </Dialog>
  );
}
