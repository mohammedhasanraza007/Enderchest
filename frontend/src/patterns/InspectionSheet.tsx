import { useRef, useState } from "react";
import { api } from "../api/endpoints";
import type { InspectionCreate } from "../api/endpoints";
import { useRefreshInventory } from "../api/queries";
import { useSingleFlight } from "../hooks/useSingleFlight";
import { useUnsavedGuard } from "../hooks/useUnsavedGuard";
import { formatDay } from "../lib/format";
import { splitProblems } from "../lib/formErrors";
import { Button } from "../primitives/Button";
import { Chip } from "../primitives/Chip";
import { TextArea } from "../primitives/Input";
import { Sheet } from "../primitives/Overlay";
import { useToast } from "../primitives/Toast";

// The inspection sheet (PAGES.md P-04): Good, Worn or Defective, a note, an optional photo. An
// inspection completes the item's maintenance task; Worn and Defective leave the item in use and
// raise "inspection suggested" (DATA_MODEL 2.10, never "replacement required").

type Result = InspectionCreate["result"];

const RESULTS: Array<{ value: Result; label: string }> = [
  { value: "ok", label: "Good" },
  { value: "worn", label: "Worn" },
  { value: "defective", label: "Defective" },
];

export const RESULT_WORDS: Record<Result, string> = {
  ok: "Good",
  worn: "Worn",
  defective: "Defective",
};

const SHOWN_FIELDS = ["result", "note", "photo_id"] as const;

interface InspectionSheetProps {
  open: boolean;
  onClose: () => void;
  item: { public_id: string; name: string };
}

export function InspectionSheet(props: InspectionSheetProps) {
  // A fresh form each time it opens.
  return props.open ? <OpenSheet {...props} /> : null;
}

function OpenSheet({ onClose, item }: InspectionSheetProps) {
  const refresh = useRefreshInventory();
  const toast = useToast();
  const once = useSingleFlight();
  const picker = useRef<HTMLInputElement>(null);
  const [result, setResult] = useState<Result | null>(null);
  const [note, setNote] = useState("");
  const [photo, setPhoto] = useState<File | null>(null);
  const [problems, setProblems] = useState<Record<string, string>>({});
  const [general, setGeneral] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  useUnsavedGuard(result !== null || note !== "" || photo !== null);

  function save() {
    if (result === null) return;
    setGeneral(null);
    once((done) => {
      setSaving(true);
      (async () => {
        // The photo becomes one of the item's photos first, then the inspection points at it.
        const photoId = photo ? (await api.addPhoto(item.public_id, photo)).id : null;
        return api.addInspection(item.public_id, { result, note: note.trim(), photo_id: photoId });
      })()
        .then(async (saved) => {
          await refresh();
          const next = saved.task?.enabled
            ? ` Next inspection ${formatDay(saved.task.next_due)}.`
            : "";
          toast({
            message:
              result === "ok"
                ? `Inspection saved.${next}`
                : `Inspection saved: inspection suggested (${RESULT_WORDS[result].toLowerCase()}).`,
          });
          onClose();
        })
        .catch((error: unknown) => {
          const found = splitProblems(error, SHOWN_FIELDS);
          setProblems(found.fields);
          setGeneral(found.general);
        })
        .finally(() => {
          setSaving(false);
          done();
        });
    });
  }

  return (
    <Sheet open onClose={onClose} title={`Inspect ${item.name}`}>
      <form
        className="stack"
        noValidate
        onSubmit={(event) => {
          event.preventDefault();
          save();
        }}
      >
        <fieldset className="plain-fieldset">
          <legend className="field__label">Result</legend>
          <div className="chip-row" role="radiogroup" aria-label="Result">
            {RESULTS.map((option) => (
              <Chip
                key={option.value}
                role="radio"
                selected={result === option.value}
                onSelect={() => setResult(option.value)}
              >
                {option.label}
              </Chip>
            ))}
          </div>
          {problems["result"] ? <p className="field__error">{problems["result"]}</p> : null}
        </fieldset>
        <p className="section-note">
          Worn or defective keeps the item in use and adds “inspection suggested” to your reminders,
          with the choice to mark it discarded.
        </p>
        <TextArea
          label="Note (optional)"
          value={note}
          onChange={(event) => setNote(event.target.value)}
          error={problems["note"]}
          rows={3}
        />
        <div className="tight-stack">
          <input
            ref={picker}
            type="file"
            accept="image/jpeg,image/png,image/webp"
            hidden
            onChange={(event) => {
              setPhoto(event.target.files?.[0] ?? null);
              event.target.value = "";
            }}
          />
          <div className="chip-row">
            <Button variant="secondary" onClick={() => picker.current?.click()}>
              {photo ? "Choose another photo" : "Add a photo (optional)"}
            </Button>
            {photo ? (
              <Button variant="ghost" onClick={() => setPhoto(null)}>
                Remove photo
              </Button>
            ) : null}
          </div>
          {photo ? <p className="section-note">Photo: {photo.name}</p> : null}
          {problems["photo_id"] ? <p className="field__error">{problems["photo_id"]}</p> : null}
        </div>
        {general ? (
          <p role="alert" className="form-failure">
            {general}
          </p>
        ) : null}
        <div className="sheet-actions">
          {result === null ? (
            <Button type="submit" disabled disabledReason="Choose Good, Worn or Defective.">
              Save inspection
            </Button>
          ) : (
            <Button type="submit" loading={saving}>
              Save inspection
            </Button>
          )}
          <Button variant="ghost" onClick={onClose}>
            Cancel
          </Button>
        </div>
      </form>
    </Sheet>
  );
}
