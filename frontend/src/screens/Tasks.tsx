import { useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api/endpoints";
import type { TaskScope, TaskView } from "../api/endpoints";
import { useRefreshInventory, useRoad, useTasks } from "../api/queries";
import { usePageTitle } from "../hooks/usePageTitle";
import { formatDay } from "../lib/format";
import { repeatText } from "../lib/notifications";
import { ErrorState } from "../patterns/ErrorState";
import { InspectionSheet } from "../patterns/InspectionSheet";
import { OverflowMenu } from "../patterns/OverflowMenu";
import { Road } from "../patterns/Road";
import { TaskFormSheet } from "../patterns/TaskFormSheet";
import { Button } from "../primitives/Button";
import { Chip } from "../primitives/Chip";
import { GlassCard } from "../primitives/Glass";
import { Skeleton } from "../primitives/Skeleton";
import { StatusChip } from "../primitives/StatusChip";
import { useToast } from "../primitives/Toast";

// P-10, Tasks: the 30-day road on top (the dashboard's road component, D-103), then filter pills
// Due soon / All / Done (D-106) and the rows, each with Mark done (or Inspect now for a
// maintenance task), Skip, Edit and Delete.

const ROAD_DAYS = 30;

const FILTERS: Array<{ scope: TaskScope; label: string; note: string; empty: string }> = [
  {
    scope: "due",
    label: "Due soon",
    note: "Overdue, or due in the next 7 days.",
    empty: "Nothing is due in the next 7 days.",
  },
  { scope: "all", label: "All", note: "Every task, switched off ones too.", empty: "" },
  {
    scope: "done",
    label: "Done",
    note: "Tasks marked done, newest first.",
    empty: "Nothing done yet.",
  },
];

export function Tasks() {
  usePageTitle("Tasks");
  const [scope, setScope] = useState<TaskScope>("due");
  const [creating, setCreating] = useState(false);
  const list = useTasks(scope);
  const all = useTasks("all");
  const filter = FILTERS.find((entry) => entry.scope === scope) ?? FILTERS[0]!;
  const none = all.data !== undefined && all.data.items.length === 0;
  const road = useRoad(ROAD_DAYS);

  return (
    <div className="tasks-page">
      <div className="page-head">
        <h1 className="page-title">Tasks</h1>
        <div className="page-head__actions">
          <Button onClick={() => setCreating(true)}>New task</Button>
        </div>
      </div>
      {road.isPending ? (
        <Skeleton height={27} />
      ) : road.isError ? (
        <ErrorState message={road.error.message} onRetry={() => void road.refetch()} />
      ) : (
        <Road
          road={road.data}
          title="Next 30 days"
          emptyText="No tasks or expiries in the next 30 days."
        />
      )}
      <GlassCard>
        <div className="stack">
          <div className="chip-row" role="radiogroup" aria-label="Show">
            {FILTERS.map((entry) => (
              <Chip
                key={entry.scope}
                role="radio"
                selected={scope === entry.scope}
                onSelect={() => setScope(entry.scope)}
              >
                {entry.label}
              </Chip>
            ))}
          </div>
          <p className="section-note">{filter.note}</p>
          {list.isPending ? (
            <div className="stack" aria-busy="true">
              <Skeleton height={64} />
              <Skeleton height={64} />
            </div>
          ) : list.isError ? (
            <ErrorState message={list.error.message} onRetry={() => void list.refetch()} />
          ) : none ? (
            <div className="empty-state">
              <p>No tasks yet.</p>
              <Button onClick={() => setCreating(true)}>New task</Button>
            </div>
          ) : list.data.items.length === 0 ? (
            <div className="empty-state">
              <p>{filter.empty}</p>
            </div>
          ) : (
            <ul className="row-list">
              {list.data.items.map((task) => (
                <TaskRow key={task.id} task={task} />
              ))}
            </ul>
          )}
        </div>
      </GlassCard>
      <TaskFormSheet open={creating} onClose={() => setCreating(false)} />
    </div>
  );
}

function TaskRow({ task }: { task: TaskView }) {
  const refresh = useRefreshInventory();
  const toast = useToast();
  const [busy, setBusy] = useState(false);
  const [failure, setFailure] = useState<string | null>(null);
  const [editing, setEditing] = useState(false);
  const [inspecting, setInspecting] = useState(false);
  const overdue = task.enabled && task.word.endsWith("overdue");
  const dueToday = task.enabled && task.word === "due today";

  async function act(work: () => Promise<void>) {
    if (busy) return;
    setBusy(true);
    setFailure(null);
    try {
      await work();
      await refresh();
    } catch (error) {
      setFailure(error instanceof Error ? error.message : "Not done.");
    } finally {
      setBusy(false);
    }
  }

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

  const complete = (how: "done" | "skip") =>
    void act(async () => {
      const { task: saved, event_id } =
        how === "done" ? await api.taskDone(task.id) : await api.taskSkip(task.id);
      const next = saved.enabled ? ` Next due ${formatDay(saved.next_due)}.` : "";
      undoable(`${how === "done" ? "Done" : "Skipped"}.${next}`, event_id);
    });

  const remove = () =>
    void act(async () => {
      const { event_id } = await api.deleteTask(task.id);
      undoable(`${task.title} deleted.`, event_id);
    });

  const switchOn = () =>
    void act(async () => {
      await api.changeTask(task.id, { enabled: true });
      toast({ message: `${task.title} is on again.` });
    });

  return (
    <li className="row-list__row task-row">
      <div className="row-list__text">
        <span className="task-row__title">{task.title}</span>
        <span className="section-note">
          {task.item ? (
            <>
              <Link to={`/items/${task.item.public_id}`}>{task.item.name}</Link>
              {" · "}
            </>
          ) : null}
          {repeatText(task)}
          {task.last_done ? ` · last done ${formatDay(task.last_done)}` : ""}
        </span>
        {failure ? (
          <span role="alert" className="field__error">
            {failure}
          </span>
        ) : null}
      </div>
      <span className="task-row__chips">
        {task.source === "gemini" ? (
          <StatusChip kind="info">suggested, unverified</StatusChip>
        ) : null}
        {overdue ? (
          <StatusChip kind="warning">{task.word}</StatusChip>
        ) : dueToday ? (
          <StatusChip kind="warning">{task.word}</StatusChip>
        ) : (
          <span className="task-row__word">
            {task.enabled ? `${task.word} · ${formatDay(task.next_due)}` : task.word}
          </span>
        )}
      </span>
      <span className="task-row__actions">
        {task.enabled ? (
          task.kind === "maintenance" && task.item ? (
            <Button onClick={() => setInspecting(true)}>Inspect now</Button>
          ) : (
            <Button loading={busy} onClick={() => complete("done")}>
              Mark done
            </Button>
          )
        ) : (
          <Button variant="secondary" loading={busy} onClick={switchOn}>
            Switch on
          </Button>
        )}
        <OverflowMenu
          label={`More for ${task.title}`}
          actions={[
            ...(task.enabled ? [{ label: "Skip", onSelect: () => complete("skip") }] : []),
            { label: "Edit", onSelect: () => setEditing(true) },
            { label: "Delete", onSelect: remove },
          ]}
        />
      </span>
      <TaskFormSheet open={editing} onClose={() => setEditing(false)} editing={task} />
      {task.item ? (
        <InspectionSheet open={inspecting} onClose={() => setInspecting(false)} item={task.item} />
      ) : null}
    </li>
  );
}
