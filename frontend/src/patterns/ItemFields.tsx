import { useState } from "react";
import type { ReactNode } from "react";
import { Minus, Plus, X } from "lucide-react";
import { api } from "../api/endpoints";
import type { Category, Location } from "../api/endpoints";
import { useCategories, useLocations, useRefreshInventory } from "../api/queries";
import { splitProblems } from "../lib/formErrors";
import { applyCategoryDefaults, normaliseKey } from "../lib/itemForm";
import type { ExpiryMode, ItemFormValues } from "../lib/itemForm";
import { Button } from "../primitives/Button";
import { Chip } from "../primitives/Chip";
import { Input, Select, TextArea } from "../primitives/Input";
import { Toggle } from "../primitives/Toggle";
import type { FieldSource, ProposalField } from "../lib/proposals";
import { SourceTag } from "./Reading";

// The item fields in the order of PAGES.md P-05. Used by the item form sheet (create, edit,
// duplicate) and by the draft confirm screen (P-07). The parent owns the values; this only draws
// them and reports each change. New categories and locations can be made inline.

export function locationLabel(location: Location): string {
  return location.path.join(" › ");
}

const EXPIRY_CHOICES: Array<{ value: ExpiryMode; label: string }> = [
  { value: "date", label: "Has date" },
  { value: "none", label: "No expiry" },
  { value: "unknown", label: "Not sure" },
];
const SUGGESTED_KEYS = ["size", "model", "part_no", "brand", "colour"];

interface ItemFieldsProps {
  values: ItemFormValues;
  onChange: (next: ItemFormValues) => void;
  problems: Record<string, string>;
  /** A new item takes its category's defaults; an edit keeps what the owner chose. */
  categoryDefaults: boolean;
  /** Where each read value came from (P-07, confirm screen only). */
  sources?: Partial<Record<ProposalField, FieldSource>>;
  /** Under the expiry date: the confirmation of a read date (P-07). */
  expiryNote?: ReactNode;
}

function tag(source: FieldSource | undefined): ReactNode {
  return source ? <SourceTag source={source} /> : undefined;
}

const READ_ATTRIBUTES: ProposalField[] = ["model", "size", "brand"];

function attributeSource(
  sources: Partial<Record<ProposalField, FieldSource>>,
  key: string,
): FieldSource | undefined {
  const field = READ_ATTRIBUTES.find((entry) => entry === normaliseKey(key));
  return field ? sources[field] : undefined;
}

export function ItemFields({
  values,
  onChange,
  problems,
  categoryDefaults,
  sources = {},
  expiryNote,
}: ItemFieldsProps) {
  const categories = useCategories();
  const locations = useLocations();
  const set = <K extends keyof ItemFormValues>(key: K, value: ItemFormValues[K]) =>
    onChange({ ...values, [key]: value });

  function chooseCategory(id: number | null, made?: Category) {
    const category = made ?? (categories.data ?? []).find((entry) => entry.id === id);
    onChange(
      categoryDefaults ? applyCategoryDefaults(values, category) : { ...values, category_id: id },
    );
  }

  const quantity = Number(values.quantity);
  return (
    <div className="item-fields">
      <Input
        label="Name"
        value={values.name}
        aside={tag(sources.name)}
        onChange={(event) => set("name", event.target.value)}
        error={problems["name"]}
        maxLength={120}
        required
      />

      <div className="item-fields__pair">
        <Select
          label="Category"
          aside={tag(sources.category_id)}
          value={values.category_id === null ? "" : String(values.category_id)}
          onChange={(event) =>
            chooseCategory(event.target.value === "" ? null : Number(event.target.value))
          }
          options={[
            { value: "", label: categories.isPending ? "Loading…" : "No category" },
            ...(categories.data ?? []).map((c) => ({ value: String(c.id), label: c.name })),
          ]}
          error={problems["category_id"]}
        />
        <NewCategory onMade={(made) => chooseCategory(made.id, made)} />
      </div>

      <div className="item-fields__quantity">
        <Input
          label="Quantity"
          inputMode="numeric"
          value={values.quantity}
          onChange={(event) => set("quantity", event.target.value)}
          error={problems["quantity"]}
          hint="Identical units that share one expiry date."
        />
        <div className="item-fields__steppers">
          {Number.isInteger(quantity) && quantity > 0 ? (
            <Button
              variant="secondary"
              aria-label="One less"
              onClick={() => set("quantity", String(quantity - 1))}
            >
              <Minus size={18} strokeWidth={1.5} aria-hidden="true" />
            </Button>
          ) : (
            <Button
              variant="secondary"
              aria-label="One less"
              disabled
              disabledReason="0 is the least."
            >
              <Minus size={18} strokeWidth={1.5} aria-hidden="true" />
            </Button>
          )}
          <Button
            variant="secondary"
            aria-label="One more"
            onClick={() => set("quantity", String(Number.isInteger(quantity) ? quantity + 1 : 1))}
          >
            <Plus size={18} strokeWidth={1.5} aria-hidden="true" />
          </Button>
        </div>
      </div>

      <div className="item-fields__pair">
        <Select
          label="Location"
          value={values.location_id === null ? "" : String(values.location_id)}
          onChange={(event) =>
            set("location_id", event.target.value === "" ? null : Number(event.target.value))
          }
          options={[
            { value: "", label: locations.isPending ? "Loading…" : "No location" },
            ...(locations.data ?? []).map((l) => ({
              value: String(l.id),
              label: locationLabel(l),
            })),
          ]}
          error={problems["location_id"]}
        />
        <NewLocation
          locations={locations.data ?? []}
          onMade={(made) => set("location_id", made.id)}
        />
      </div>

      <fieldset className="item-fields__expiry">
        <legend className="field__label">Expiry</legend>
        <div className="chip-row" role="radiogroup" aria-label="Expiry">
          {EXPIRY_CHOICES.map((choice) => (
            <Chip
              key={choice.value}
              role="radio"
              selected={values.expiry_mode === choice.value}
              onSelect={() =>
                onChange({
                  ...values,
                  expiry_mode: choice.value,
                  expiry_date: choice.value === "date" ? values.expiry_date : "",
                })
              }
            >
              {choice.label}
            </Chip>
          ))}
        </div>
        {values.expiry_mode === "date" ? (
          <Input
            label="Expiry date"
            type="date"
            aside={tag(sources.expiry_date)}
            value={values.expiry_date}
            onChange={(event) => set("expiry_date", event.target.value)}
            error={problems["expiry_date"]}
          />
        ) : problems["expiry_date"] ? (
          <p className="field__error">{problems["expiry_date"]}</p>
        ) : null}
        {values.expiry_mode === "date" ? expiryNote : null}
      </fieldset>

      <Input
        label="Price of one (₹, optional)"
        inputMode="decimal"
        value={values.price}
        onChange={(event) => set("price", event.target.value)}
        error={problems["price_paise"]}
        placeholder="1240"
      />

      <AttributeRows
        values={values}
        onChange={onChange}
        error={problems["attributes"]}
        sources={sources}
      />

      <TextArea
        label="Notes"
        rows={3}
        value={values.notes}
        onChange={(event) => set("notes", event.target.value)}
        error={problems["notes"]}
        maxLength={2000}
      />

      <Toggle
        label="I don't need a printed label"
        checked={values.no_label_needed}
        onChange={(next) => set("no_label_needed", next)}
      />
    </div>
  );
}

function AttributeRows({
  values,
  onChange,
  error,
  sources,
}: {
  values: ItemFormValues;
  onChange: (next: ItemFormValues) => void;
  error?: string;
  sources: Partial<Record<ProposalField, FieldSource>>;
}) {
  const rows = values.attributes;
  const setRows = (next: typeof rows) => onChange({ ...values, attributes: next });
  const unused = SUGGESTED_KEYS.filter((key) => !rows.some((row) => row.key === key));
  return (
    <fieldset className="item-fields__attributes">
      <legend className="field__label">Attributes</legend>
      {rows.map((row, index) => (
        <div className="attribute-row" key={index}>
          <Input
            label="Name"
            value={row.key}
            onChange={(event) =>
              setRows(rows.map((r, i) => (i === index ? { ...r, key: event.target.value } : r)))
            }
          />
          <Input
            label="Value"
            value={row.value}
            aside={tag(attributeSource(sources, row.key))}
            hint="Commas make a list: 8, 10, 12"
            onChange={(event) =>
              setRows(rows.map((r, i) => (i === index ? { ...r, value: event.target.value } : r)))
            }
          />
          <Button
            variant="ghost"
            aria-label={`Remove attribute ${row.key || index + 1}`}
            onClick={() => setRows(rows.filter((_, i) => i !== index))}
          >
            <X size={18} strokeWidth={1.5} aria-hidden="true" />
          </Button>
        </div>
      ))}
      {error ? <p className="field__error">{error}</p> : null}
      <div className="chip-row">
        {unused.map((key) => (
          <Chip key={key} onSelect={() => setRows([...rows, { key, value: "" }])}>
            + {key}
          </Chip>
        ))}
        <Chip onSelect={() => setRows([...rows, { key: "", value: "" }])}>+ Other</Chip>
      </div>
    </fieldset>
  );
}

/** "New category": a name, then the new category is chosen in the form. */
function NewCategory({ onMade }: { onMade: (made: Category) => void }) {
  const [open, setOpen] = useState(false);
  const [name, setName] = useState("");
  const [problem, setProblem] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const refresh = useRefreshInventory();

  if (!open) {
    return (
      <Button variant="ghost" onClick={() => setOpen(true)}>
        New category
      </Button>
    );
  }
  async function add() {
    if (busy) return;
    setBusy(true);
    setProblem(null);
    try {
      const made = await api.createCategory({ name });
      await refresh();
      onMade(made);
      setOpen(false);
      setName("");
    } catch (error) {
      const found = splitProblems(error, ["name"]);
      setProblem(found.fields["name"] ?? found.general);
    } finally {
      setBusy(false);
    }
  }
  return (
    <div className="inline-add">
      <Input
        label="New category name"
        value={name}
        autoFocus
        onChange={(event) => setName(event.target.value)}
        error={problem ?? undefined}
        onKeyDown={(event) => {
          if (event.key === "Enter") {
            event.preventDefault();
            void add();
          }
        }}
      />
      {name.trim() === "" ? (
        <Button disabled disabledReason="Type a name first.">
          Add
        </Button>
      ) : (
        <Button loading={busy} onClick={() => void add()}>
          Add
        </Button>
      )}
      <Button variant="ghost" onClick={() => setOpen(false)}>
        Cancel
      </Button>
    </div>
  );
}

/** "New location": a name and the place it sits in. */
function NewLocation({
  locations,
  onMade,
}: {
  locations: Location[];
  onMade: (made: Location) => void;
}) {
  const [open, setOpen] = useState(false);
  const [name, setName] = useState("");
  const [parent, setParent] = useState("");
  const [problem, setProblem] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const refresh = useRefreshInventory();

  if (!open) {
    return (
      <Button variant="ghost" onClick={() => setOpen(true)}>
        New location
      </Button>
    );
  }
  async function add() {
    if (busy) return;
    setBusy(true);
    setProblem(null);
    try {
      const made = await api.createLocation({
        name,
        parent_id: parent === "" ? null : Number(parent),
      });
      await refresh();
      onMade(made);
      setOpen(false);
      setName("");
    } catch (error) {
      const found = splitProblems(error, ["name", "parent_id"]);
      setProblem(found.fields["name"] ?? found.fields["parent_id"] ?? found.general);
    } finally {
      setBusy(false);
    }
  }
  return (
    <div className="inline-add">
      <Input
        label="New location name"
        value={name}
        autoFocus
        onChange={(event) => setName(event.target.value)}
        // Enter adds the place: this form sits inside the item form, which it must not submit.
        onKeyDown={(event) => {
          if (event.key === "Enter") {
            event.preventDefault();
            void add();
          }
        }}
        error={problem ?? undefined}
      />
      <Select
        label="Inside"
        value={parent}
        onChange={(event) => setParent(event.target.value)}
        options={[
          { value: "", label: "Nothing (a top-level place)" },
          ...locations.map((l) => ({ value: String(l.id), label: locationLabel(l) })),
        ]}
      />
      {name.trim() === "" ? (
        <Button disabled disabledReason="Type a name first.">
          Add
        </Button>
      ) : (
        <Button loading={busy} onClick={() => void add()}>
          Add
        </Button>
      )}
      <Button variant="ghost" onClick={() => setOpen(false)}>
        Cancel
      </Button>
    </div>
  );
}
