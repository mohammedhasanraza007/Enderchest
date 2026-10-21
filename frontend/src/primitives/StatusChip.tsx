import type { ReactNode } from "react";
import { CircleAlert, CircleCheck, CircleX, Info } from "lucide-react";

// The only place a status colour is used for text on glass (DESIGN.md 4.5): a dark pill with an
// icon and a word in the semantic colour. Status is never colour alone.

export type StatusKind = "success" | "warning" | "danger" | "info";

const ICONS = { success: CircleCheck, warning: CircleAlert, danger: CircleX, info: Info } as const;

export function StatusChip({ kind, children }: { kind: StatusKind; children: ReactNode }) {
  const Icon = ICONS[kind];
  return (
    <span className={`status-chip status-chip--${kind}`}>
      <Icon size={16} strokeWidth={1.5} aria-hidden="true" />
      {children}
    </span>
  );
}
