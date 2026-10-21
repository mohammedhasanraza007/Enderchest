import type { ReactNode } from "react";

// Chips and filters (DESIGN.md 6.12): pills at the secondary-pill level; a selected chip uses
// the active-tab fill.

interface ChipProps {
  children: ReactNode;
  /** Present for a chip that can be chosen; leave out for a plain label. */
  selected?: boolean;
  onSelect?: () => void;
  /** "radio" when the chips are a group where exactly one is chosen (for example the theme). */
  role?: "radio";
}

export function Chip({ children, selected, onSelect, role }: ChipProps) {
  if (onSelect === undefined) {
    return <span className="chip">{children}</span>;
  }
  return (
    <button
      type="button"
      className={["chip", "chip--button", selected ? "is-selected" : ""].filter(Boolean).join(" ")}
      role={role}
      aria-checked={role === "radio" ? Boolean(selected) : undefined}
      aria-pressed={role === "radio" ? undefined : Boolean(selected)}
      onClick={onSelect}
    >
      {children}
    </button>
  );
}
