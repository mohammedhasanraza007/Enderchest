import type { NotificationAction, NotificationView, TaskView } from "../api/endpoints";

// Pure helpers for reminder rows and task rows (PAGES.md P-10, P-11; DESIGN.md 6.9). The words
// come from the server (D-106); these only arrange them.

/** What the row is about: the item's name, else the task's title. */
export function rowName(row: NotificationView): string {
  return row.item?.name ?? row.task?.title ?? "Reminder";
}

/** "Oat milk (expires today)", the row text of DESIGN.md 6.9. */
export function rowLabel(row: NotificationView): string {
  return `${rowName(row)} (${row.word})`;
}

/** The first two actions show as pills; the rest go in the row's More menu (API 1). */
export function splitActions(actions: NotificationAction[]): {
  pills: NotificationAction[];
  more: NotificationAction[];
} {
  return { pills: actions.slice(0, 2), more: actions.slice(2) };
}

export const RESOLUTION_WORDS: Record<string, string> = {
  used: "Used",
  expired_marked: "Marked expired",
  discarded: "Discarded",
  done: "Done",
  skipped: "Skipped",
  inspected: "Inspected",
  dismissed: "Kept in use",
  superseded: "No longer needed",
};

export function resolutionWord(resolution: string | null): string {
  return resolution ? (RESOLUTION_WORDS[resolution] ?? resolution) : "";
}

/** "every 14 days" or "one-off", and how a repeat counts (DATA_MODEL 2.9). */
export function repeatText(task: Pick<TaskView, "interval_days" | "schedule_mode">): string {
  if (task.interval_days === null) return "one-off";
  const every = task.interval_days === 1 ? "every day" : `every ${task.interval_days} days`;
  return task.schedule_mode === "fixed" ? `${every}, fixed dates` : every;
}

/** The Notification API, if this browser has one, and its permission state. */
export type BrowserPermission = NotificationPermission | "unsupported";

export function browserPermission(): BrowserPermission {
  return typeof window !== "undefined" && "Notification" in window
    ? window.Notification.permission
    : "unsupported";
}

export const PERMISSION_WORDS: Record<BrowserPermission, string> = {
  granted: "Allowed: browser notifications appear while an Enderchest tab is open.",
  default: "Not allowed yet.",
  denied: "Blocked in this browser. Allow them in the browser's site settings for this page.",
  unsupported: "This browser cannot show notifications. Reminders still appear here.",
};
