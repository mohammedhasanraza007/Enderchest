// Money is stored as integer paise and shown as rupees with Indian digit grouping (CLAUDE.md 5,
// DESIGN.md 12): 124500000 paise is "₹12,45,000".

/** "₹1,240" or "₹1,240.50" from paise; never negative. */
export function formatRupees(paise: number): string {
  const safe = Math.max(0, Math.round(paise));
  const rupees = Math.floor(safe / 100);
  const rest = safe % 100;
  const grouped = new Intl.NumberFormat("en-IN").format(rupees);
  return rest === 0 ? `₹${grouped}` : `₹${grouped}.${String(rest).padStart(2, "0")}`;
}

/**
 * Typed rupees to paise: "1,240", "₹ 1240.5" and "1240.50" all work. Returns null for an empty
 * field and NaN for text that is not an amount (the form shows the problem).
 */
export function parseRupees(text: string): number | null {
  const cleaned = text.replace(/[₹,\s]/g, "");
  if (cleaned === "") return null;
  if (!/^\d+(\.\d{1,2})?$/.test(cleaned)) return Number.NaN;
  const [whole, fraction = ""] = cleaned.split(".");
  return Number(whole) * 100 + Number(fraction.padEnd(2, "0"));
}

/** Paise back to the plain text a price field shows ("1240.5" becomes "1240.50"). */
export function paiseToInput(paise: number | null | undefined): string {
  if (paise === null || paise === undefined) return "";
  const rest = paise % 100;
  return rest === 0
    ? String(paise / 100)
    : `${Math.floor(paise / 100)}.${String(rest).padStart(2, "0")}`;
}
