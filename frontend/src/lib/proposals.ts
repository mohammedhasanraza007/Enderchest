// Values read from the photo or suggested by Gemini, and the form (PAGES.md P-07, D-100, D-101).
// A proposal fills a field only while the owner has not made that field their own; each field
// then shows where its value came from. Nothing here talks to the server.

import type { Proposal } from "../api/endpoints";
import { normaliseKey } from "./itemForm";
import type { ItemFormValues } from "./itemForm";

/** The proposal keys that map onto form fields (the inspection interval is Phase 4's). */
export const PROPOSAL_FIELDS = [
  "name",
  "category_id",
  "expiry_date",
  "model",
  "size",
  "brand",
] as const;
export type ProposalField = (typeof PROPOSAL_FIELDS)[number];

export type Proposed = Record<string, Proposal>;
export type Source = "ocr" | "gemini" | "you";

export interface FieldSource {
  source: Source;
  confidence?: Proposal["confidence"];
  flags?: string[];
}

export const SOURCE_LABEL: Record<Source, string> = {
  ocr: "Read from photo",
  gemini: "Gemini, unverified",
  you: "You",
};

/** Plain words for the parser's flags, shown beside a read date and in the drawer. */
export const FLAG_WORDS: Record<string, string> = {
  ambiguous: "the day and month could be either way round",
  month_only: "only a month and year are printed, so the last day of the month is used",
  computed: "worked out from the manufacture date and the shelf life",
  ocr_fix: "letters that look like digits were read as digits",
  unlabelled: "no EXP or Best before label next to it",
  far_past: "more than 10 years ago",
  far_future: "more than 15 years ahead",
  unverified: "not checked by this app",
  suggested: "a suggestion only",
};

/** The value a field has in the form now, as text, to compare with a proposal. */
export function formValue(values: ItemFormValues, field: ProposalField): string {
  if (field === "name") return values.name.trim();
  if (field === "expiry_date") return values.expiry_mode === "date" ? values.expiry_date : "";
  if (field === "category_id") return values.category_id === null ? "" : String(values.category_id);
  const row = values.attributes.find((entry) => normaliseKey(entry.key) === field);
  return row ? row.value.trim() : "";
}

/** The form with one proposal written into its field. */
export function withProposal(
  values: ItemFormValues,
  field: ProposalField,
  proposal: Proposal,
): ItemFormValues {
  const value = String(proposal.value);
  if (field === "name") return { ...values, name: value };
  if (field === "expiry_date") return { ...values, expiry_mode: "date", expiry_date: value };
  if (field === "category_id") return { ...values, category_id: Number(proposal.value) };
  const index = values.attributes.findIndex((entry) => normaliseKey(entry.key) === field);
  const attributes =
    index === -1
      ? [...values.attributes, { key: field, value }]
      : values.attributes.map((entry, i) => (i === index ? { ...entry, value } : entry));
  return { ...values, attributes };
}

/**
 * The fields the owner has made their own: a value that is not what was proposed. A deliberate
 * "No expiry" counts as the owner's choice too.
 */
export function ownedFields(
  values: ItemFormValues,
  proposed: Proposed,
  saved: readonly ProposalField[] = [],
): Set<ProposalField> {
  // `saved` is the list the draft kept: a field the owner cleared looks untouched otherwise.
  const owned = new Set<ProposalField>(saved);
  for (const field of PROPOSAL_FIELDS) {
    const current = formValue(values, field);
    const proposal = proposed[field];
    if (current !== "" && (!proposal || String(proposal.value) !== current)) owned.add(field);
  }
  if (values.expiry_mode === "none") owned.add("expiry_date");
  return owned;
}

/** Fill every field the owner has not made their own from its proposal. */
export function applyProposals(
  values: ItemFormValues,
  proposed: Proposed,
  owned: Set<ProposalField>,
): ItemFormValues {
  let next = values;
  for (const field of PROPOSAL_FIELDS) {
    const proposal = proposed[field];
    if (proposal && !owned.has(field)) next = withProposal(next, field, proposal);
  }
  return next;
}

/** Which fields an edit changed, so they become the owner's. */
export function changedFields(before: ItemFormValues, after: ItemFormValues): ProposalField[] {
  const changed = PROPOSAL_FIELDS.filter(
    (field) => formValue(before, field) !== formValue(after, field),
  );
  if (before.expiry_mode !== after.expiry_mode && !changed.includes("expiry_date")) {
    changed.push("expiry_date");
  }
  return changed;
}

/** Where a field's current value came from, or null when the field is empty. */
export function sourceOf(
  values: ItemFormValues,
  field: ProposalField,
  proposed: Proposed,
): FieldSource | null {
  const current = formValue(values, field);
  if (current === "") return null;
  const proposal = proposed[field];
  if (proposal && String(proposal.value) === current) {
    return { source: proposal.source, confidence: proposal.confidence, flags: proposal.flags };
  }
  return { source: "you" };
}

/** Sources for every proposal field that has a value (attributes by their key). */
export function sourcesFor(
  values: ItemFormValues,
  proposed: Proposed,
): Partial<Record<ProposalField, FieldSource>> {
  const sources: Partial<Record<ProposalField, FieldSource>> = {};
  for (const field of PROPOSAL_FIELDS) {
    const found = sourceOf(values, field, proposed);
    if (found) sources[field] = found;
  }
  return sources;
}
