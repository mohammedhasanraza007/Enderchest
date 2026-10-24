import { describe, expect, it } from "vitest";
import type { NotificationView } from "../api/endpoints";
import { repeatText, rowLabel, splitActions } from "./notifications";
import { emptyTask, taskValues, toCreate, toPatch, validateTask } from "./taskForm";
import { titleText } from "./title";

const row: NotificationView = {
  id: 1,
  kind: "expiry_soon",
  item: { public_id: "ENDR-7K2M9QXA", name: "Oat milk", primary_photo_id: null },
  task: null,
  due_date: "2026-10-24",
  word: "expires today",
  urgency: "today",
  status: "open",
  snoozed_until: null,
  read_at: null,
  resolution: null,
  actions: [
    { key: "mark_expired", label: "Mark expired", primary: true },
    { key: "snooze", label: "Snooze", primary: false },
    { key: "use", label: "Use it", primary: false },
    { key: "discard", label: "Discard", primary: false },
  ],
};

describe("reminder rows", () => {
  it("reads like the reference: name, then the word in brackets", () => {
    expect(rowLabel(row)).toBe("Oat milk (expires today)");
    expect(rowLabel({ ...row, item: null, task: { id: 3, title: "Clean PC" } })).toBe(
      "Clean PC (expires today)",
    );
  });

  it("shows two pills and puts the rest in More", () => {
    const { pills, more } = splitActions(row.actions);
    expect(pills.map((a) => a.key)).toEqual(["mark_expired", "snooze"]);
    expect(more.map((a) => a.key)).toEqual(["use", "discard"]);
  });

  it("describes a repeat", () => {
    expect(repeatText({ interval_days: null, schedule_mode: "from_completion" })).toBe("one-off");
    expect(repeatText({ interval_days: 1, schedule_mode: "from_completion" })).toBe("every day");
    expect(repeatText({ interval_days: 14, schedule_mode: "fixed" })).toBe(
      "every 14 days, fixed dates",
    );
  });
});

describe("tab title", () => {
  it("adds the open count in front only while it is above zero", () => {
    expect(titleText("Tasks", 0)).toBe("Tasks · Enderchest");
    expect(titleText("Tasks", 3)).toBe("(3) Tasks · Enderchest");
    expect(titleText(undefined, 2)).toBe("(2) Enderchest");
  });
});

describe("task form", () => {
  it("names the field of each problem", () => {
    const values = { ...emptyTask("2026-10-24"), repeats: true, interval: "0" };
    expect(Object.keys(validateTask(values))).toEqual(["title", "interval_days"]);
    expect(Object.keys(validateTask({ ...values, title: "A", interval: "7", due: "" }))).toEqual([
      "first_due",
    ]);
    expect(
      Object.keys(validateTask({ ...values, title: "A", interval: "7", due: "x" }, true)),
    ).toEqual(["next_due"]);
  });

  it("builds a create body; no repeat means a one-off", () => {
    const values = { ...emptyTask("2026-10-24"), title: " Clean PC ", interval: "14" };
    expect(toCreate(values)).toEqual({
      title: "Clean PC",
      kind: "chore",
      enabled: true,
      item_public_id: null,
      interval_days: null,
      schedule_mode: "from_completion",
      first_due: "2026-10-24",
      notes: "",
    });
    expect(toCreate({ ...values, repeats: true, schedule: "fixed" }).interval_days).toBe(14);
  });

  it("sends only what changed on an edit", () => {
    const start = taskValues({
      id: 1,
      title: "Clean PC",
      kind: "chore",
      item: null,
      interval_days: 14,
      schedule_mode: "from_completion",
      next_due: "2026-10-24",
      last_done: null,
      enabled: true,
      source: "user",
      notes: "",
      word: "due today",
    });
    expect(toPatch(start, start, false)).toEqual({});
    expect(toPatch(start, { ...start, repeats: false }, false)).toEqual({ interval_days: null });
    expect(toPatch(start, { ...start, due: "2026-10-30", title: "Dust PC" }, false)).toEqual({
      title: "Dust PC",
      next_due: "2026-10-30",
    });
  });
});

describe("dates for forms", () => {
  it("gives today in the owner's zone and moves by whole days", async () => {
    const { addDays, localToday } = await import("./format");
    expect(localToday("Asia/Kolkata", new Date("2026-10-23T20:00:00Z"))).toBe("2026-10-24");
    expect(localToday("UTC", new Date("2026-10-23T20:00:00Z"))).toBe("2026-10-23");
    expect(addDays("2026-10-24", 30)).toBe("2026-11-23");
    expect(addDays("2026-12-31", 1)).toBe("2027-01-01");
  });
});
