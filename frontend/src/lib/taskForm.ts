import type { TaskCreate, TaskPatch, TaskView } from "../api/endpoints";

// The New task / Edit task form (PAGES.md P-10): values as text while typing, a pure check, and
// the request bodies. A repeat is "none" or every N days; a fixed schedule keeps the original
// series of dates (DATA_MODEL 2.9).

export interface TaskFormValues {
  title: string;
  item: { public_id: string; name: string } | null;
  repeats: boolean;
  interval: string;
  schedule: "from_completion" | "fixed";
  due: string;
  notes: string;
}

/**
 * The request fields the form shows right now, for splitProblems: a problem on any other field
 * becomes the general message, never a hidden one (F-024).
 */
export function shownTaskFields(values: TaskFormValues, editing: boolean, maintenance: boolean) {
  return [
    "title",
    ...(maintenance ? [] : ["item_public_id"]),
    ...(values.repeats ? ["interval_days"] : []),
    editing ? "next_due" : "first_due",
    "notes",
  ];
}

export function emptyTask(today: string): TaskFormValues {
  return {
    title: "",
    item: null,
    repeats: false,
    interval: "",
    schedule: "from_completion",
    due: today,
    notes: "",
  };
}

export function taskValues(task: TaskView): TaskFormValues {
  return {
    title: task.title,
    item: task.item,
    repeats: task.interval_days !== null,
    interval: task.interval_days === null ? "" : String(task.interval_days),
    schedule: task.schedule_mode,
    due: task.next_due,
    notes: task.notes,
  };
}

const DATE = /^\d{4}-\d{2}-\d{2}$/;

/** Problems by request field name, in the order they are shown. */
export function validateTask(values: TaskFormValues, editing = false): Record<string, string> {
  const problems: Record<string, string> = {};
  const title = values.title.trim();
  if (title.length === 0) problems["title"] = "Give the task a title.";
  else if (title.length > 120) problems["title"] = "Keep the title to 120 characters.";
  if (values.repeats) {
    const days = Number(values.interval);
    if (!/^\d+$/.test(values.interval.trim()) || days < 1 || days > 3650) {
      problems["interval_days"] = "Repeat every 1 to 3650 days.";
    }
  }
  if (!DATE.test(values.due) || Number.isNaN(Date.parse(`${values.due}T00:00:00Z`))) {
    problems[editing ? "next_due" : "first_due"] = "Choose the date it is due.";
  }
  if (values.notes.length > 2000) problems["notes"] = "Notes can be up to 2000 characters.";
  return problems;
}

export function toCreate(values: TaskFormValues): TaskCreate {
  return {
    title: values.title.trim(),
    kind: "chore",
    enabled: true,
    item_public_id: values.item?.public_id ?? null,
    interval_days: values.repeats ? Number(values.interval) : null,
    schedule_mode: values.repeats ? values.schedule : "from_completion",
    first_due: values.due,
    notes: values.notes.trim(),
  };
}

/** Only what changed, so an edit never rewrites a field the owner did not touch. */
export function toPatch(start: TaskFormValues, values: TaskFormValues, maintenance: boolean) {
  const patch: TaskPatch = {};
  if (values.title.trim() !== start.title.trim()) patch.title = values.title.trim();
  if (!maintenance && values.item?.public_id !== start.item?.public_id) {
    patch.item_public_id = values.item?.public_id ?? null;
  }
  const interval = values.repeats ? Number(values.interval) : null;
  const startInterval = start.repeats ? Number(start.interval) : null;
  if (interval !== startInterval) patch.interval_days = interval;
  if (values.repeats && values.schedule !== start.schedule) patch.schedule_mode = values.schedule;
  if (values.due !== start.due) patch.next_due = values.due;
  if (values.notes.trim() !== start.notes.trim()) patch.notes = values.notes.trim();
  return patch;
}
