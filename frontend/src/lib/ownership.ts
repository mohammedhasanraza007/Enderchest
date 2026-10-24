// "Do I own this?" and savings helpers (P-13, P-14). The page never says "certain" or "you own
// this": a level is a confidence, and the owner decides (CLAUDE.md 6, D-114).
import { parseRupees } from "./money";

export type Level = "high" | "medium" | "low";

/** The API's `low` reads "Possible" on screen (D-114). */
export const LEVEL_WORDS: Record<Level, string> = {
  high: "High",
  medium: "Medium",
  low: "Possible",
};

export const LEVEL_KIND: Record<Level, "success" | "info" | "warning"> = {
  high: "success",
  medium: "info",
  low: "warning",
};

/** The one "why" line under a candidate: its two strongest reasons. */
export function whyLine(reasons: string[]): string {
  return reasons.slice(0, 2).join(" · ") || "Some words match";
}

/** What blocks Check, or null when it may run. */
export function checkBlocked(hasPhoto: boolean, text: string): string | null {
  if (text.trim().length > 200) return "Keep the words to 200 characters.";
  return hasPhoto || text.trim() !== "" ? null : "Add a photo or type what you are looking for.";
}

/** The typed price in paise, or the problem to show. A saving needs a real, positive price. */
export function savingPrice(text: string): { paise: number } | { problem: string } {
  const paise = parseRupees(text);
  if (paise === null) return { problem: "Type the price you did not spend." };
  if (Number.isNaN(paise)) return { problem: "Type an amount such as 1,240 or 1240.50." };
  if (paise <= 0) return { problem: "The price must be more than ₹0." };
  return { paise };
}
