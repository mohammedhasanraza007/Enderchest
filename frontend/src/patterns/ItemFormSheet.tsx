import { useEffect, useState } from "react";
import { announceDelivery } from "../lib/motion";
import { api } from "../api/endpoints";
import type { ItemDetail } from "../api/endpoints";
import { idempotencyKey } from "../api/client";
import { useRefreshInventory } from "../api/queries";
import { useSingleFlight } from "../hooks/useSingleFlight";
import { useUnsavedGuard } from "../hooks/useUnsavedGuard";
import { splitProblems } from "../lib/formErrors";
import { changedPayload, emptyValues, ITEM_FIELDS, toPayload, validate } from "../lib/itemForm";
import type { ItemFormValues } from "../lib/itemForm";
import { Button } from "../primitives/Button";
import { Dialog, Sheet } from "../primitives/Overlay";
import { useToast } from "../primitives/Toast";
import { ItemFields } from "./ItemFields";

// P-05, the item form sheet: add an item by hand, edit one, or duplicate one (a new item that
// starts as a copy). Save is disabled with the reason while something is wrong; closing with
// unsaved edits asks first (PAGES.md 2).

interface ItemFormSheetProps {
  open: boolean;
  onClose: () => void;
  /** Present when editing; the sheet then sends only what changed. */
  editing?: ItemDetail;
  /** The starting values for a new item; empty when left out. */
  initial?: ItemFormValues;
  /** `initial` is a copy of an item, not just a head start on a new one. */
  duplicate?: boolean;
  onSaved: (item: ItemDetail) => void;
}

export function ItemFormSheet(props: ItemFormSheetProps) {
  // A fresh form each time the sheet opens, so old edits never leak into a new item.
  return props.open ? <OpenSheet {...props} /> : null;
}

function OpenSheet({ onClose, editing, initial, duplicate, onSaved }: ItemFormSheetProps) {
  const [start] = useState<ItemFormValues>(() => initial ?? emptyValues());
  const [values, setValues] = useState<ItemFormValues>(start);
  const [touched, setTouched] = useState<Set<string>>(new Set());
  const [serverProblems, setServerProblems] = useState<Record<string, string>>({});
  const [general, setGeneral] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const [askDiscard, setAskDiscard] = useState(false);
  const [key] = useState(idempotencyKey);
  const once = useSingleFlight();
  const refresh = useRefreshInventory();
  const toast = useToast();

  const dirty = JSON.stringify(values) !== JSON.stringify(start);
  useUnsavedGuard(dirty);
  useEffect(() => setServerProblems({}), [values]);

  const problems = validate(values);
  const shown: Record<string, string> = { ...serverProblems };
  for (const [field, message] of Object.entries(problems)) {
    if (touched.has(field) || (field === "expiry_date" && touched.has("expiry_mode"))) {
      shown[field] = message;
    }
  }
  const firstProblem = Object.values(problems)[0];
  const nothingChanged = editing !== undefined && !dirty;

  function change(next: ItemFormValues) {
    const changed = new Set(touched);
    for (const field of Object.keys(next) as Array<keyof ItemFormValues>) {
      if (JSON.stringify(next[field]) !== JSON.stringify(values[field])) {
        changed.add(field === "price" ? "price_paise" : field);
      }
    }
    setTouched(changed);
    setValues(next);
  }

  function close() {
    if (dirty && !saving) setAskDiscard(true);
    else onClose();
  }

  function save() {
    setGeneral(null);
    once((done) => {
      setSaving(true);
      const request = editing
        ? api.changeItem(editing.public_id, changedPayload(start, values))
        : api.createItem(toPayload(values), key);
      request
        .then(async (item) => {
          await refresh();
          toast({ message: editing ? "Changes saved." : "Item saved." });
          if (!editing) announceDelivery();
          onSaved(item);
          onClose();
        })
        .catch((error: unknown) => {
          const found = splitProblems(error, ITEM_FIELDS);
          setServerProblems(found.fields);
          setGeneral(found.general);
        })
        .finally(() => {
          setSaving(false);
          done();
        });
    });
  }

  const title = editing ? `Edit ${editing.name}` : duplicate ? "Duplicate item" : "Add an item";
  return (
    <>
      <Sheet open onClose={close} title={title}>
        <form
          className="stack"
          noValidate
          onSubmit={(event) => {
            event.preventDefault();
            if (!firstProblem && !nothingChanged) save();
          }}
        >
          <ItemFields
            values={values}
            onChange={change}
            problems={shown}
            categoryDefaults={editing === undefined}
          />
          {general ? (
            <p role="alert" className="form-failure">
              {general}
            </p>
          ) : null}
          <div className="sheet-actions">
            {firstProblem ? (
              <Button type="submit" disabled disabledReason={firstProblem}>
                Save item
              </Button>
            ) : nothingChanged ? (
              <Button type="submit" disabled disabledReason="Change something to save.">
                Save item
              </Button>
            ) : (
              <Button type="submit" loading={saving}>
                Save item
              </Button>
            )}
            <Button variant="ghost" onClick={close}>
              Cancel
            </Button>
          </div>
        </form>
      </Sheet>
      <Dialog open={askDiscard} onClose={() => setAskDiscard(false)} title="Discard your changes?">
        <p>What you typed in this form will be lost.</p>
        <div className="sheet-actions">
          <Button
            onClick={() => {
              setAskDiscard(false);
              onClose();
            }}
          >
            Discard changes
          </Button>
          <Button variant="secondary" onClick={() => setAskDiscard(false)}>
            Keep editing
          </Button>
        </div>
      </Dialog>
    </>
  );
}
