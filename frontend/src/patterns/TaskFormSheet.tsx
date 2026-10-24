import { useEffect, useId, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { api } from "../api/endpoints";
import type { TaskView } from "../api/endpoints";
import { idempotencyKey } from "../api/client";
import { useProfile, useRefreshInventory } from "../api/queries";
import { useSingleFlight } from "../hooks/useSingleFlight";
import { useUnsavedGuard } from "../hooks/useUnsavedGuard";
import { localToday } from "../lib/format";
import { splitProblems } from "../lib/formErrors";
import {
  emptyTask,
  shownTaskFields,
  taskValues,
  toCreate,
  toPatch,
  validateTask,
} from "../lib/taskForm";
import type { TaskFormValues } from "../lib/taskForm";
import { Button } from "../primitives/Button";
import { Chip } from "../primitives/Chip";
import { Input, TextArea } from "../primitives/Input";
import { Dialog, Sheet } from "../primitives/Overlay";
import { useToast } from "../primitives/Toast";

// New task and Edit task (PAGES.md P-10): title, an optional item, repeat (none or every N
// days), schedule (from completion or fixed dates), the due date and notes. Save is disabled with
// the reason while something is wrong; closing with edits asks first (PAGES.md 2, F-024).

interface TaskFormSheetProps {
  open: boolean;
  onClose: () => void;
  /** Present when editing; the sheet then sends only what changed. */
  editing?: TaskView;
}

export function TaskFormSheet(props: TaskFormSheetProps) {
  return props.open ? <OpenSheet {...props} /> : null;
}

function OpenSheet({ onClose, editing }: TaskFormSheetProps) {
  const timeZone = useProfile().data?.timezone ?? "UTC";
  const [start] = useState<TaskFormValues>(() =>
    editing ? taskValues(editing) : emptyTask(localToday(timeZone)),
  );
  const [values, setValues] = useState<TaskFormValues>(start);
  const [touched, setTouched] = useState<Set<string>>(new Set());
  const [serverProblems, setServerProblems] = useState<Record<string, string>>({});
  const [general, setGeneral] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const [askDiscard, setAskDiscard] = useState(false);
  const [key] = useState(idempotencyKey);
  const once = useSingleFlight();
  const refresh = useRefreshInventory();
  const toast = useToast();
  const maintenance = editing?.kind === "maintenance";
  const dueField = editing ? "next_due" : "first_due";

  const dirty = JSON.stringify(values) !== JSON.stringify(start);
  useUnsavedGuard(dirty);
  useEffect(() => setServerProblems({}), [values]);

  const problems = validateTask(values, editing !== undefined);
  const shown: Record<string, string> = { ...serverProblems };
  for (const [field, message] of Object.entries(problems)) {
    if (touched.has(field)) shown[field] = message;
  }
  const firstProblem = Object.values(problems)[0];
  const nothingChanged = editing !== undefined && !dirty;

  function change(next: Partial<TaskFormValues>, field: string) {
    setTouched(new Set(touched).add(field));
    setValues({ ...values, ...next });
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
        ? api.changeTask(editing.id, toPatch(start, values, maintenance))
        : api.createTask(toCreate(values), key);
      request
        .then(async () => {
          await refresh();
          toast({ message: editing ? "Task saved." : "Task added." });
          onClose();
        })
        .catch((error: unknown) => {
          const found = splitProblems(
            error,
            shownTaskFields(values, editing !== undefined, maintenance),
          );
          setServerProblems(found.fields);
          setGeneral(found.general);
        })
        .finally(() => {
          setSaving(false);
          done();
        });
    });
  }

  return (
    <>
      <Sheet open onClose={close} title={editing ? `Edit ${editing.title}` : "New task"}>
        <form
          className="stack"
          noValidate
          onSubmit={(event) => {
            event.preventDefault();
            if (!firstProblem && !nothingChanged) save();
          }}
        >
          <Input
            label="Title"
            value={values.title}
            onChange={(event) => change({ title: event.target.value }, "title")}
            error={shown["title"]}
            maxLength={120}
          />
          {maintenance ? (
            <p className="section-note">Item: {values.item?.name}</p>
          ) : (
            <ItemPicker
              value={values.item}
              onChange={(item) => change({ item }, "item_public_id")}
              error={shown["item_public_id"]}
            />
          )}
          <fieldset className="plain-fieldset tight-stack">
            <legend className="field__label">Repeat</legend>
            <div className="chip-row" role="radiogroup" aria-label="Repeat">
              <Chip
                role="radio"
                selected={!values.repeats}
                onSelect={() => change({ repeats: false }, "repeats")}
              >
                Does not repeat
              </Chip>
              <Chip
                role="radio"
                selected={values.repeats}
                onSelect={() => change({ repeats: true }, "repeats")}
              >
                Every few days
              </Chip>
            </div>
          </fieldset>
          {values.repeats ? (
            <>
              <Input
                label="Every how many days"
                inputMode="numeric"
                value={values.interval}
                onChange={(event) => change({ interval: event.target.value }, "interval_days")}
                error={shown["interval_days"]}
              />
              <fieldset className="plain-fieldset tight-stack">
                <legend className="field__label">Next date counts from</legend>
                <div className="chip-row" role="radiogroup" aria-label="Next date counts from">
                  <Chip
                    role="radio"
                    selected={values.schedule === "from_completion"}
                    onSelect={() => change({ schedule: "from_completion" }, "schedule_mode")}
                  >
                    The day it is done
                  </Chip>
                  <Chip
                    role="radio"
                    selected={values.schedule === "fixed"}
                    onSelect={() => change({ schedule: "fixed" }, "schedule_mode")}
                  >
                    Fixed dates
                  </Chip>
                </div>
                <p className="section-note">
                  {values.schedule === "fixed"
                    ? "Fixed dates keep the same calendar series, even when it is done late."
                    : "The next one is due that many days after you mark it done."}
                </p>
              </fieldset>
            </>
          ) : null}
          <Input
            label={editing ? "Next due" : "First due"}
            type="date"
            value={values.due}
            onChange={(event) => change({ due: event.target.value }, dueField)}
            error={shown[dueField]}
          />
          <TextArea
            label="Notes (optional)"
            value={values.notes}
            onChange={(event) => change({ notes: event.target.value }, "notes")}
            error={shown["notes"]}
            rows={3}
          />
          {general ? (
            <p role="alert" className="form-failure">
              {general}
            </p>
          ) : null}
          <div className="sheet-actions">
            {firstProblem ? (
              <Button type="submit" disabled disabledReason={firstProblem}>
                Save task
              </Button>
            ) : nothingChanged ? (
              <Button type="submit" disabled disabledReason="Change something to save.">
                Save task
              </Button>
            ) : (
              <Button type="submit" loading={saving}>
                Save task
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

/** An optional item: type part of a name, pick one of the matches; the choice shows as a chip. */
function ItemPicker({
  value,
  onChange,
  error,
}: {
  value: TaskFormValues["item"];
  onChange: (item: TaskFormValues["item"]) => void;
  error?: string;
}) {
  const [text, setText] = useState("");
  const listId = useId();
  const words = text.trim();
  const matches = useQuery({
    queryKey: ["items", { q: words, picker: true }],
    queryFn: () => api.items({ q: words, sort: "name_asc" }),
    enabled: words.length > 0 && value === null,
  });
  if (value !== null) {
    return (
      <div className="tight-stack">
        <span className="field__label">Item</span>
        <div className="chip-row">
          <span className="chip">{value.name}</span>
          <Button variant="ghost" onClick={() => onChange(null)}>
            Remove item
          </Button>
        </div>
        {error ? <p className="field__error">{error}</p> : null}
      </div>
    );
  }
  const found = matches.data?.items.slice(0, 6) ?? [];
  return (
    <div className="tight-stack">
      <Input
        label="Item (optional)"
        hint="Type part of its name, then choose it."
        value={text}
        onChange={(event) => setText(event.target.value)}
        error={error}
        aria-controls={listId}
      />
      {words.length > 0 ? (
        <ul id={listId} className="picker-list" aria-label="Matching items">
          {matches.isPending ? (
            <li className="section-note">Looking…</li>
          ) : found.length === 0 ? (
            <li className="section-note">No item matches “{words}”.</li>
          ) : (
            found.map((item) => (
              <li key={item.public_id}>
                <button
                  type="button"
                  className="picker-list__option"
                  onClick={() => {
                    onChange({ public_id: item.public_id, name: item.name });
                    setText("");
                  }}
                >
                  {item.name}
                  {item.location_path.length > 0 ? (
                    <span className="section-note"> · {item.location_path.join(" › ")}</span>
                  ) : null}
                </button>
              </li>
            ))
          )}
        </ul>
      ) : null}
    </div>
  );
}
