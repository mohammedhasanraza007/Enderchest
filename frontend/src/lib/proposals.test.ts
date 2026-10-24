import { describe, expect, it } from "vitest";
import type { Proposal } from "../api/endpoints";
import { emptyValues } from "./itemForm";
import {
  applyProposals,
  changedFields,
  ownedFields,
  sourceOf,
  sourcesFor,
  withProposal,
} from "./proposals";

const read = (value: string | number, extra: Partial<Proposal> = {}): Proposal => ({
  value,
  source: "ocr",
  confidence: "high",
  flags: [],
  ...extra,
});

const PROPOSED = {
  name: read("Oat Milk"),
  model: read("AB-1234X"),
  size: read("500 ml"),
  expiry_date: read("2027-03-14"),
  inspection_interval_days: read(180, { source: "gemini", confidence: "medium" }),
};

describe("proposals", () => {
  it("fill an empty form, attributes as rows", () => {
    const filled = applyProposals(emptyValues(), PROPOSED, new Set());
    expect(filled.name).toBe("Oat Milk");
    expect(filled.expiry_mode).toBe("date");
    expect(filled.expiry_date).toBe("2027-03-14");
    expect(filled.attributes).toEqual([
      { key: "model", value: "AB-1234X" },
      { key: "size", value: "500 ml" },
    ]);
  });

  it("never overwrite a field the owner made their own", () => {
    const typed = { ...emptyValues(), name: "My oat milk" };
    const owned = ownedFields(typed, PROPOSED);
    expect([...owned]).toEqual(["name"]);
    expect(applyProposals(typed, PROPOSED, owned).name).toBe("My oat milk");
  });

  it("keep a field the owner cleared as theirs after a reload (D-100)", () => {
    const cleared = { ...emptyValues(), name: "Oat Milk" };
    const owned = ownedFields(cleared, PROPOSED, ["model", "expiry_date"]);
    const filled = applyProposals(cleared, PROPOSED, owned);
    expect(filled.attributes).toEqual([{ key: "size", value: "500 ml" }]);
    expect(filled.expiry_date).toBe("");
  });

  it("treat a deliberate No expiry as the owner's", () => {
    const none = { ...emptyValues(), expiry_mode: "none" as const };
    const filled = applyProposals(none, PROPOSED, ownedFields(none, PROPOSED));
    expect(filled.expiry_mode).toBe("none");
  });

  it("replace an existing attribute row of the same key", () => {
    const withRow = { ...emptyValues(), attributes: [{ key: "Model", value: "" }] };
    expect(withProposal(withRow, "model", read("X-1")).attributes).toEqual([
      { key: "Model", value: "X-1" },
    ]);
  });

  it("say where each value came from", () => {
    const filled = applyProposals(emptyValues(), PROPOSED, new Set());
    expect(sourceOf(filled, "name", PROPOSED)).toEqual({
      source: "ocr",
      confidence: "high",
      flags: [],
    });
    const edited = { ...filled, name: "Oat milk, barista" };
    expect(sourceOf(edited, "name", PROPOSED)).toEqual({ source: "you" });
    expect(sourceOf(emptyValues(), "name", PROPOSED)).toBeNull();
  });

  it("tag read attributes, and the owner's own values as theirs", () => {
    const values = {
      ...applyProposals(emptyValues(), PROPOSED, new Set()),
      attributes: [
        { key: "model", value: "AB-1234X" },
        { key: "colour", value: "red" },
        { key: "size", value: "1 L" },
      ],
    };
    const sources = sourcesFor(values, PROPOSED);
    expect(sources.model?.source).toBe("ocr");
    expect(sources.size).toEqual({ source: "you" });
    expect(sources.brand).toBeUndefined();
    expect(sources.name?.source).toBe("ocr");
  });

  it("notice which fields an edit changed", () => {
    const filled = applyProposals(emptyValues(), PROPOSED, new Set());
    expect(changedFields(filled, { ...filled, name: "Other" })).toEqual(["name"]);
    expect(changedFields(filled, { ...filled, expiry_mode: "unknown", expiry_date: "" })).toEqual([
      "expiry_date",
    ]);
    expect(changedFields(filled, { ...filled, notes: "x" })).toEqual([]);
  });
});
