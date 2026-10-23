// The item form's values and how they map to the API (PAGES.md P-05, DATA_MODEL 2.6). Text
// fields stay text while the owner types; they become numbers, paise and lists only here.

import type {
  AttrValue,
  Category,
  DraftFields,
  ItemCreate,
  ItemDetail,
  ItemPatch,
} from "../api/endpoints";
import { paiseToInput, parseRupees } from "./money";

export type ExpiryMode = "date" | "none" | "unknown";

export interface AttributeRow {
  key: string;
  value: string;
}

export interface ItemFormValues {
  name: string;
  category_id: number | null;
  quantity: string;
  location_id: number | null;
  expiry_mode: ExpiryMode;
  expiry_date: string;
  price: string;
  attributes: AttributeRow[];
  notes: string;
  no_label_needed: boolean;
}

/** The API fields this form shows; a server problem on any other field is a general message. */
export const ITEM_FIELDS = [
  "name",
  "category_id",
  "quantity",
  "location_id",
  "expiry_mode",
  "expiry_date",
  "price_paise",
  "attributes",
  "notes",
  "no_label_needed",
] as const;

const ATTR_KEY = /^[a-z][a-z0-9_]{0,39}$/;
const DATE = /^\d{4}-\d{2}-\d{2}$/;

export function emptyValues(): ItemFormValues {
  return {
    name: "",
    category_id: null,
    quantity: "1",
    location_id: null,
    expiry_mode: "unknown",
    expiry_date: "",
    price: "",
    attributes: [],
    notes: "",
    no_label_needed: false,
  };
}

export function attributesToRows(attributes: Record<string, AttrValue>): AttributeRow[] {
  return Object.entries(attributes).map(([key, value]) => ({
    key,
    value: Array.isArray(value) ? value.join(", ") : String(value),
  }));
}

/** "Part No" becomes "part_no", the shape the server accepts. */
export function normaliseKey(key: string): string {
  return key
    .trim()
    .toLowerCase()
    .replace(/[\s-]+/g, "_");
}

function scalar(text: string): string | number {
  const number = Number(text);
  // Only text that reads back the same becomes a number, so "007" and "M8" stay text.
  return text !== "" && Number.isFinite(number) && String(number) === text ? number : text;
}

/** Comma-separated values become a list: "8, 10, 12" is [8, 10, 12]. */
export function rowsToAttributes(rows: AttributeRow[]): Record<string, AttrValue> {
  const result: Record<string, AttrValue> = {};
  for (const row of rows) {
    const key = normaliseKey(row.key);
    if (key === "" && row.value.trim() === "") continue;
    const parts = row.value
      .split(",")
      .map((part) => part.trim())
      .filter((part) => part !== "");
    result[key] = parts.length > 1 ? parts.map(scalar) : scalar(parts[0] ?? "");
  }
  return result;
}

export function valuesFromItem(item: ItemDetail): ItemFormValues {
  return {
    name: item.name,
    category_id: item.category?.id ?? null,
    quantity: String(item.quantity),
    location_id: item.location?.id ?? null,
    expiry_mode: item.expiry.mode,
    expiry_date: item.expiry.date ?? "",
    price: paiseToInput(item.price_paise),
    attributes: attributesToRows(item.attributes),
    notes: item.notes,
    no_label_needed: item.label.no_label_needed,
  };
}

export function valuesFromDraft(fields: DraftFields): ItemFormValues {
  const empty = emptyValues();
  return {
    name: fields.name ?? "",
    category_id: fields.category_id ?? null,
    quantity:
      fields.quantity === undefined || fields.quantity === null ? "1" : String(fields.quantity),
    location_id: fields.location_id ?? null,
    expiry_mode: fields.expiry_mode ?? (fields.expiry_date ? "date" : empty.expiry_mode),
    expiry_date: fields.expiry_date ?? "",
    price: paiseToInput(fields.price_paise),
    attributes: attributesToRows(fields.attributes ?? {}),
    notes: fields.notes ?? "",
    no_label_needed: fields.no_label_needed ?? false,
  };
}

/** A new item in a category starts with that category's defaults (DATA_MODEL 2.4). */
export function applyCategoryDefaults(
  values: ItemFormValues,
  category: Category | undefined,
): ItemFormValues {
  if (!category) return { ...values, category_id: null };
  return {
    ...values,
    category_id: category.id,
    expiry_mode: category.expires_default ? "date" : "none",
    expiry_date: category.expires_default ? values.expiry_date : "",
    no_label_needed: !category.label_default,
  };
}

/** Problems the owner can fix before saving, keyed like the API fields. */
export function validate(values: ItemFormValues): Record<string, string> {
  const problems: Record<string, string> = {};
  const name = values.name.trim();
  if (name.length < 1 || name.length > 120)
    problems["name"] = "Enter a name of 1 to 120 characters.";
  if (!/^\d+$/.test(values.quantity.trim()) || Number(values.quantity) > 1_000_000) {
    problems["quantity"] = "Enter a whole number, 0 or more.";
  }
  if (values.expiry_mode === "date" && !DATE.test(values.expiry_date)) {
    problems["expiry_date"] = "Enter the expiry date, or choose No expiry or Not sure.";
  }
  if (Number.isNaN(parseRupees(values.price)))
    problems["price_paise"] = "Enter an amount like 1240 or 1240.50.";
  if (values.notes.trim().length > 2000) problems["notes"] = "Notes can be up to 2000 characters.";
  for (const row of values.attributes) {
    const key = normaliseKey(row.key);
    if (key === "" && row.value.trim() === "") continue;
    if (!ATTR_KEY.test(key)) {
      problems["attributes"] = "Attribute names start with a letter: size, model, part_no.";
    } else if (row.value.trim() === "") {
      problems["attributes"] = "Give each attribute a value.";
    }
  }
  return problems;
}

/** The whole item as POST /items takes it. Call only when `validate` found nothing. */
export function toPayload(values: ItemFormValues): ItemCreate {
  return {
    name: values.name.trim(),
    category_id: values.category_id,
    quantity: Number(values.quantity),
    location_id: values.location_id,
    expiry_mode: values.expiry_mode,
    expiry_date: values.expiry_mode === "date" ? values.expiry_date : null,
    price_paise: parseRupees(values.price),
    attributes: rowsToAttributes(values.attributes),
    notes: values.notes.trim(),
    no_label_needed: values.no_label_needed,
  };
}

/** Only what changed, for PATCH /items/{public_id}. */
export function changedPayload(initial: ItemFormValues, current: ItemFormValues): ItemPatch {
  const before = toPayload(initial) as Record<string, unknown>;
  const after = toPayload(current) as Record<string, unknown>;
  const changes: Record<string, unknown> = {};
  for (const key of Object.keys(after)) {
    if (JSON.stringify(before[key]) !== JSON.stringify(after[key])) changes[key] = after[key];
  }
  return changes as ItemPatch;
}

/**
 * The fields a draft can store right now (PAGES.md P-07, saved as the owner edits): a value
 * still being typed wrongly is left out instead of being refused.
 */
export function toDraftFields(values: ItemFormValues, expiryConfirmed: boolean): DraftFields {
  const problems = validate({ ...values, name: values.name.trim() === "" ? "x" : values.name });
  const fields: DraftFields = {
    name: values.name.trim(),
    category_id: values.category_id,
    location_id: values.location_id,
    expiry_mode: values.expiry_mode,
    no_label_needed: values.no_label_needed,
    expiry_confirmed: expiryConfirmed,
  };
  if (!problems["quantity"]) fields.quantity = Number(values.quantity);
  fields.expiry_date =
    values.expiry_mode === "date" && !problems["expiry_date"] ? values.expiry_date : null;
  if (!problems["price_paise"]) fields.price_paise = parseRupees(values.price);
  if (!problems["attributes"]) fields.attributes = rowsToAttributes(values.attributes);
  if (!problems["notes"]) fields.notes = values.notes.trim();
  return fields;
}
