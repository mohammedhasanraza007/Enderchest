import { describe, expect, it } from "vitest";
import { ApiError } from "../api/client";
import { splitProblems } from "./formErrors";
import { isPublicId } from "./ids";
import { filtersFromQuery, isFiltered, queryFromFilters } from "./inventoryQuery";
import {
  applyCategoryDefaults,
  changedPayload,
  emptyValues,
  rowsToAttributes,
  toDraftFields,
  toPayload,
  validate,
} from "./itemForm";
import { formatRupees, paiseToInput, parseRupees } from "./money";

describe("money", () => {
  it("groups rupees the Indian way and keeps paise", () => {
    expect(formatRupees(124_500_000)).toBe("₹12,45,000");
    expect(formatRupees(124_050)).toBe("₹1,240.50");
    expect(formatRupees(-5)).toBe("₹0");
  });
  it("reads typed amounts", () => {
    expect(parseRupees("1,240")).toBe(124_000);
    expect(parseRupees("₹ 1240.5")).toBe(124_050);
    expect(parseRupees("")).toBeNull();
    expect(parseRupees("12.345")).toBeNaN();
    expect(paiseToInput(124_050)).toBe("1240.50");
  });
});

describe("item form", () => {
  it("turns comma-separated values into lists and keeps codes as text", () => {
    expect(
      rowsToAttributes([
        { key: "Sizes", value: "8, 10, 12" },
        { key: "Part No", value: "007" },
        { key: "", value: "" },
      ]),
    ).toEqual({ sizes: [8, 10, 12], part_no: "007" });
  });
  it("finds the problems before saving", () => {
    const values = { ...emptyValues(), quantity: "-1", expiry_mode: "date" as const, price: "x" };
    expect(Object.keys(validate(values)).sort()).toEqual([
      "expiry_date",
      "name",
      "price_paise",
      "quantity",
    ]);
  });
  it("builds the create body and only the changes for an edit", () => {
    const start = { ...emptyValues(), name: " Tape ", price: "50" };
    expect(toPayload(start)).toMatchObject({ name: "Tape", price_paise: 5000, expiry_date: null });
    expect(changedPayload(start, { ...start, price: "" })).toEqual({ price_paise: null });
  });
  it("applies category defaults", () => {
    const food = {
      id: 3,
      name: "Food",
      expires_default: true,
      maintenance_default: false,
      label_default: false,
      item_count: 0,
    };
    const next = applyCategoryDefaults(emptyValues(), food);
    expect([next.expiry_mode, next.no_label_needed]).toEqual(["date", true]);
  });
  it("leaves half-typed values out of a draft", () => {
    const fields = toDraftFields({ ...emptyValues(), quantity: "abc", price: "12" }, true);
    expect(fields.quantity).toBeUndefined();
    expect(fields.price_paise).toBe(1200);
  });
});

describe("form problems (F-024)", () => {
  it("puts shown fields under the field and the rest in one message", () => {
    const error = new ApiError(422, "validation_error", "Some values are not valid.", {
      problems: [
        { field: "name", problem: "Enter a name." },
        { field: "secret_field", problem: "Hidden problem." },
      ],
    });
    expect(splitProblems(error, ["name"])).toEqual({
      fields: { name: "Enter a name." },
      general: "Hidden problem.",
    });
  });
  it("maps a duplicate-name conflict to the name field", () => {
    const error = new ApiError(409, "conflict", "That name exists.", { field: "name" });
    expect(splitProblems(error, ["name"]).fields).toEqual({ name: "That name exists." });
    expect(splitProblems(error, []).general).toBe("That name exists.");
  });
});

describe("inventory query", () => {
  it("round-trips filters and drops defaults", () => {
    const query = new URLSearchParams("q=tape&category=3&photo=no&sort=name_asc&state=bogus");
    const filters = filtersFromQuery(query);
    expect(filters).toMatchObject({ q: "tape", category_id: 3, has_photo: false, state: "active" });
    expect(queryFromFilters(filters).toString()).toBe("q=tape&category=3&photo=no&sort=name_asc");
    expect(isFiltered(filtersFromQuery(new URLSearchParams("sort=name_asc")))).toBe(false);
  });
  it("recognises public ids", () => {
    expect(isPublicId("ENDR-7K2M9QXA")).toBe(true);
    expect(isPublicId("ENDR-7K2M9QXU")).toBe(false);
    expect(isPublicId("https://example.com")).toBe(false);
  });
});
