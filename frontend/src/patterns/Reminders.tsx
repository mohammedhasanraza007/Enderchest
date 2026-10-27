import { useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api/endpoints";
import type { NotificationAction, NotificationView, SnoozeOption } from "../api/endpoints";
import { useRefreshInventory } from "../api/queries";
import { formatDay } from "../lib/format";
import { pause, tokenMs } from "../lib/motion";
import { resolutionWord, rowName, splitActions } from "../lib/notifications";
import { Button } from "../primitives/Button";
import { Dialog } from "../primitives/Overlay";
import { useToast } from "../primitives/Toast";
import { InspectionSheet } from "./InspectionSheet";
import { OverflowMenu } from "./OverflowMenu";

// Reminder rows (PAGES.md P-11, DESIGN.md 6.9): "Oat Milk (expires today)" with two pills below
// and the rest of the server's actions in More. The server says which actions a row has; this
// file only knows which endpoint each action calls. Reversible actions offer Undo for 10 s.

const SNOOZE: Array<{ option: SnoozeOption; label: string }> = [
  { option: "tomorrow", label: "Tomorrow" },
  { option: "3days", label: "In 3 days" },
  { option: "week", label: "Next week" },
];

interface ReminderListProps {
  rows: NotificationView[];
  /** Opening a row marks it read (P-11). */
  onOpen?: (row: NotificationView) => void;
}

export function ReminderList({ rows, onOpen }: ReminderListProps) {
  const refresh = useRefreshInventory();
  const toast = useToast();
  const [busy, setBusy] = useState<number | null>(null);
  const [leaving, setLeaving] = useState<number | null>(null);
  const [failure, setFailure] = useState<{ id: number; message: string } | null>(null);
  const [snoozing, setSnoozing] = useState<NotificationView | null>(null);
  const [inspecting, setInspecting] = useState<NotificationView | null>(null);

  /** Runs a row action. When the action resolves the row (`work` answers `leaves: true`), the
   * row slides out before the list refreshes (DESIGN.md 10.1: motion shows what changed); under
   * reduced motion the pause is 0 ms. */
  async function act(
    row: NotificationView,
    work: () => Promise<{ message: string | null; leaves: boolean }>,
  ) {
    if (busy !== null) return;
    setBusy(row.id);
    setFailure(null);
    try {
      const { message, leaves } = await work();
      if (leaves) {
        setLeaving(row.id);
        await pause(tokenMs("--dur-base"));
      }
      await refresh();
      if (message) toast({ message });
    } catch (error) {
      setFailure({ id: row.id, message: error instanceof Error ? error.message : "Not done." });
    } finally {
      setLeaving(null);
      setBusy(null);
    }
  }

  /** A toast with Undo for a reversible action; a failed undo says why. */
  function undoable(message: string, eventId: number) {
    toast({
      message,
      actionLabel: "Undo",
      onAction: () =>
        void api
          .undo(eventId)
          .then(refresh)
          .catch((error: unknown) =>
            toast({ message: error instanceof Error ? error.message : "Undo did not work." }),
          ),
    });
  }

  function run(row: NotificationView, action: NotificationAction) {
    const publicId = row.item?.public_id;
    const taskId = row.task?.id;
    switch (action.key) {
      case "snooze":
        setSnoozing(row);
        return;
      case "inspect":
        setInspecting(row);
        return;
      case "keep":
        void act(row, async () => {
          await api.dismiss(row.id);
          return { message: `${rowName(row)} stays in use.`, leaves: true };
        });
        return;
      case "use":
      case "mark_expired":
      case "discard":
        if (publicId === undefined) return;
        void act(row, async () => {
          const call =
            action.key === "use"
              ? api.markUsed(publicId)
              : action.key === "discard"
                ? api.discard(publicId)
                : api.markExpired(publicId);
          const { item, event_id } = await call;
          const word =
            action.key === "use"
              ? item.state === "used"
                ? "used up"
                : `used one, ${item.quantity} left`
              : action.key === "discard"
                ? "discarded"
                : "marked expired";
          undoable(`${item.name} ${word}.`, event_id);
          return { message: null, leaves: item.state !== "active" };
        });
        return;
      case "done":
      case "skip":
        if (taskId === undefined) return;
        void act(row, async () => {
          const { task, event_id } =
            action.key === "done" ? await api.taskDone(taskId) : await api.taskSkip(taskId);
          const next = task.enabled ? ` Next due ${formatDay(task.next_due)}.` : "";
          undoable(`${action.key === "done" ? "Done" : "Skipped"}.${next}`, event_id);
          return { message: null, leaves: true };
        });
    }
  }

  return (
    <>
      <ul className="reminder-list">
        {rows.map((row) => {
          const { pills, more } = splitActions(row.actions);
          return (
            <li
              key={row.id}
              className={`reminder${leaving === row.id ? " reminder--leaving" : ""}`}
            >
              <p className="reminder__text">
                {row.item ? (
                  <Link to={`/items/${row.item.public_id}`} onClick={() => onOpen?.(row)}>
                    {row.item.name}
                  </Link>
                ) : (
                  <span>{rowName(row)}</span>
                )}{" "}
                <span className="reminder__word">({row.word})</span>
              </p>
              {row.status === "snoozed" && row.snoozed_until ? (
                <p className="section-note">Snoozed until {formatDay(row.snoozed_until)}</p>
              ) : null}
              {row.status === "resolved" ? (
                <p className="section-note">
                  {resolutionWord(row.resolution)} · due {formatDay(row.due_date)}
                </p>
              ) : null}
              {pills.length > 0 ? (
                <div className="reminder__actions">
                  {pills.map((action) => (
                    <Button
                      key={action.key}
                      variant={action.primary ? "primary" : "secondary"}
                      loading={busy === row.id && action.key !== "snooze"}
                      onClick={() => run(row, action)}
                    >
                      {action.label}
                    </Button>
                  ))}
                  {more.length > 0 ? (
                    <OverflowMenu
                      label={`More for ${rowName(row)}`}
                      actions={more.map((action) => ({
                        label: action.label,
                        onSelect: () => run(row, action),
                      }))}
                    />
                  ) : null}
                </div>
              ) : null}
              {failure?.id === row.id ? (
                <p role="alert" className="field__error">
                  {failure.message}
                </p>
              ) : null}
            </li>
          );
        })}
      </ul>
      <SnoozeDialog row={snoozing} onClose={() => setSnoozing(null)} />
      {inspecting?.item ? (
        <InspectionSheet
          open
          onClose={() => setInspecting(null)}
          item={{ public_id: inspecting.item.public_id, name: inspecting.item.name }}
        />
      ) : null}
    </>
  );
}

/** Tomorrow / In 3 days / Next week; an expiry reminder never snoozes past its date (D-047). */
function SnoozeDialog({ row, onClose }: { row: NotificationView | null; onClose: () => void }) {
  const refresh = useRefreshInventory();
  const toast = useToast();
  const [busy, setBusy] = useState<SnoozeOption | null>(null);
  const [failure, setFailure] = useState<string | null>(null);

  async function snooze(option: SnoozeOption) {
    if (row === null || busy) return;
    setBusy(option);
    setFailure(null);
    try {
      const saved = await api.snooze(row.id, option);
      await refresh();
      toast({ message: `Snoozed until ${formatDay(saved.snoozed_until ?? row.due_date)}.` });
      onClose();
    } catch (error) {
      setFailure(error instanceof Error ? error.message : "Not snoozed.");
    } finally {
      setBusy(null);
    }
  }

  return (
    <Dialog open={row !== null} onClose={onClose} title={row ? `Snooze ${rowName(row)}` : "Snooze"}>
      <div className="stack">
        {row?.kind === "expiry_soon" ? (
          <p className="section-note">
            It comes back on {formatDay(row.due_date)} at the latest: a reminder never hides an item
            past its date.
          </p>
        ) : null}
        <div className="chip-row">
          {SNOOZE.map((choice) => (
            <Button
              key={choice.option}
              variant="secondary"
              loading={busy === choice.option}
              onClick={() => void snooze(choice.option)}
            >
              {choice.label}
            </Button>
          ))}
        </div>
        {failure ? (
          <p role="alert" className="form-failure">
            {failure}
          </p>
        ) : null}
      </div>
    </Dialog>
  );
}
