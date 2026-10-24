import { describe, expect, it } from "vitest";
import { LEVEL_WORDS, checkBlocked, savingPrice, whyLine } from "./ownership";

describe("ownership helpers", () => {
  it("never words a level as certain", () => {
    expect(Object.values(LEVEL_WORDS)).toEqual(["High", "Medium", "Possible"]);
    for (const word of Object.values(LEVEL_WORDS))
      expect(word.toLowerCase()).not.toContain("certain");
  });

  it("keeps the why line to two reasons", () => {
    expect(whyLine(["Same model number", "Same size", "Looks similar"])).toBe(
      "Same model number · Same size",
    );
    expect(whyLine([])).toBe("Some words match");
  });

  it("needs a photo or words before Check", () => {
    expect(checkBlocked(false, "  ")).toMatch(/Add a photo/);
    expect(checkBlocked(true, "")).toBeNull();
    expect(checkBlocked(false, "13 mm spanner")).toBeNull();
    expect(checkBlocked(false, "x".repeat(201))).toMatch(/200/);
  });

  it("takes a saving only with a positive typed price", () => {
    expect(savingPrice("")).toEqual({ problem: "Type the price you did not spend." });
    expect(savingPrice("0")).toEqual({ problem: "The price must be more than ₹0." });
    expect(savingPrice("abc")).toHaveProperty("problem");
    expect(savingPrice("₹1,240.50")).toEqual({ paise: 124050 });
  });
});
