import { useState } from "react";
import { api } from "../api/endpoints";
import type { ItemDetail, MaintenanceBody } from "../api/endpoints";
import { useCategories, useInspections, useProfile, useRefreshInventory } from "../api/queries";
import { useSingleFlight } from "../hooks/useSingleFlight";
import { addDays, formatDay, localToday } from "../lib/format";
import { splitProblems } from "../lib/formErrors";
import { Button } from "../primitives/Button";
import { GlassCard, InnerPanel } from "../primitives/Glass";
import { Input } from "../primitives/Input";
import { Skeleton } from "../primitives/Skeleton";
import { StatusChip } from "../primitives/StatusChip";
import { Toggle } from "../primitives/Toggle";
import { useToast } from "../primitives/Toast";
import { ErrorState } from "./ErrorState";
import { InspectionSheet, RESULT_WORDS } from "./InspectionSheet";

// The item's Maintenance card (PAGES.md P-04): the per-item toggle, every N days, the next date,
// Inspect now and the past inspections. A Gemini interval is "suggested, unverified" until the
// owner confirms or changes it (D-102); a category with maintenance on opens the plan form but
// never switches it on by itself (DATA_MODEL 2.4). Wording is "inspection suggested", never
// "replacement required" (CLAUDE.md 6).

const SHOWN_FIELDS = ["interval_days", "first_due"] as const;

export function MaintenanceCard({ item }: { item: ItemDetail }) {
  const categories = useCategories();
  const plan = item.maintenance;
  const opensByDefault =
    plan === null &&
    categories.data?.find((category) => category.id === item.category?.id)?.maintenance_default ===
      true;
  const [planning, setPlanning] = useState(false);
  const [inspecting, setInspecting] = useState(false);
  const active = item.state === "active" && item.deleted_at === null;

  if (item.deleted_at !== null) {
    return (
      <GlassCard title="Maintenance" headingLevel={2}>
        <p className="section-note">Restore the item to plan or record inspections.</p>
      </GlassCard>
    );
  }

  return (
    <GlassCard title="Maintenance" headingLevel={2} className="maintenance-card">
      <div className="stack">
        {plan === null ? (
          planning || opensByDefault ? (
            <PlanForm
              item={item}
              onDone={() => setPlanning(false)}
              canCancel={planning && !opensByDefault}
            />
          ) : (
            <div className="tight-stack">
              <p className="section-note">No inspection plan yet.</p>
              <div>
                <Button variant="secondary" onClick={() => setPlanning(true)}>
                  Plan inspections
                </Button>
              </div>
            </div>
          )
        ) : planning ? (
          <PlanForm item={item} onDone={() => setPlanning(false)} canCancel />
        ) : (
          <PlanSummary item={item} />
        )}
        {active || (plan !== null && !planning) ? (
          <div className="chip-row">
            {active ? <Button onClick={() => setInspecting(true)}>Inspect now</Button> : null}
            {plan !== null && !planning ? (
              <Button variant="secondary" onClick={() => setPlanning(true)}>
                Change plan
              </Button>
            ) : null}
          </div>
        ) : null}
        <Inspections item={item} />
      </div>
      <InspectionSheet open={inspecting} onClose={() => setInspecting(false)} item={item} />
    </GlassCard>
  );
}

/** The saved plan: the toggle, how often, the next date, and Confirm for a Gemini suggestion. */
function PlanSummary({ item }: { item: ItemDetail }) {
  const plan = item.maintenance!;
  const refresh = useRefreshInventory();
  const toast = useToast();
  const once = useSingleFlight();
  const [failure, setFailure] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  function put(body: MaintenanceBody, message: string) {
    setFailure(null);
    once((done) => {
      setSaving(true);
      api
        .putMaintenance(item.public_id, body)
        .then(async () => {
          await refresh();
          toast({ message });
        })
        .catch((error: unknown) => setFailure(splitProblems(error, []).general))
        .finally(() => {
          setSaving(false);
          done();
        });
    });
  }

  return (
    <div className="tight-stack">
      <Toggle
        label="Inspection reminders"
        checked={plan.enabled}
        onChange={(next) =>
          put({ enabled: next }, next ? "Inspection reminders on." : "Inspection reminders off.")
        }
      />
      <p>
        {plan.interval_days === null
          ? "Once"
          : `Every ${plan.interval_days} ${plan.interval_days === 1 ? "day" : "days"}`}
        {plan.enabled ? ` · next due ${formatDay(plan.next_due)}` : " · switched off"}
        {plan.last_done ? ` · last done ${formatDay(plan.last_done)}` : ""}
      </p>
      {plan.source === "gemini" ? (
        <InnerPanel className="maintenance-card__suggested">
          <StatusChip kind="info">suggested, unverified</StatusChip>
          <span className="section-note">
            Gemini suggested this interval. Check it against the maker's advice.
          </span>
          <Button
            variant="secondary"
            loading={saving}
            onClick={() => put({ enabled: plan.enabled, source: "user" }, "Interval confirmed.")}
          >
            Confirm
          </Button>
        </InnerPanel>
      ) : null}
      {failure ? (
        <p role="alert" className="form-failure">
          {failure}
        </p>
      ) : null}
    </div>
  );
}

/** Every N days and the first due date; Gemini's interval can fill it, labelled as unverified. */
function PlanForm({
  item,
  onDone,
  canCancel,
}: {
  item: ItemDetail;
  onDone: () => void;
  canCancel: boolean;
}) {
  const timeZone = useProfile().data?.timezone ?? "UTC";
  const today = localToday(timeZone);
  const plan = item.maintenance;
  const suggestion = item.maintenance_suggestion;
  const refresh = useRefreshInventory();
  const toast = useToast();
  const once = useSingleFlight();
  const [every, setEvery] = useState(plan?.interval_days ? String(plan.interval_days) : "");
  const [due, setDue] = useState(plan?.next_due ?? "");
  const [fromGemini, setFromGemini] = useState(false);
  const [problems, setProblems] = useState<Record<string, string>>({});
  const [general, setGeneral] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  const days = Number(every);
  const intervalOk = /^\d+$/.test(every.trim()) && days >= 1 && days <= 3650;
  const firstDue = due || (intervalOk ? addDays(today, days) : "");
  const problem = !intervalOk ? "Inspect every 1 to 3650 days." : null;

  function save() {
    setGeneral(null);
    once((done) => {
      setSaving(true);
      api
        .putMaintenance(item.public_id, {
          enabled: true,
          interval_days: days,
          first_due: firstDue,
          source: fromGemini ? "gemini" : "user",
        })
        .then(async (task) => {
          await refresh();
          toast({ message: `Inspection reminders on. Next due ${formatDay(task.next_due)}.` });
          onDone();
        })
        .catch((error: unknown) => {
          const found = splitProblems(error, SHOWN_FIELDS);
          setProblems(found.fields);
          setGeneral(found.general);
        })
        .finally(() => {
          setSaving(false);
          done();
        });
    });
  }

  return (
    <form
      className="tight-stack"
      noValidate
      onSubmit={(event) => {
        event.preventDefault();
        if (!problem) save();
      }}
    >
      {plan === null ? (
        <p className="section-note">No inspection plan yet. Choose how often to inspect it.</p>
      ) : null}
      {suggestion && !fromGemini && String(suggestion.interval_days) !== every ? (
        <InnerPanel className="maintenance-card__suggested">
          <StatusChip kind="info">suggested, unverified</StatusChip>
          <span className="section-note">
            Gemini suggests inspecting every {suggestion.interval_days} days.
          </span>
          <Button
            variant="secondary"
            onClick={() => {
              setEvery(String(suggestion.interval_days));
              setFromGemini(true);
            }}
          >
            Use this
          </Button>
        </InnerPanel>
      ) : null}
      <Input
        label="Inspect every how many days"
        inputMode="numeric"
        value={every}
        onChange={(event) => {
          setEvery(event.target.value);
          setFromGemini(false);
        }}
        aside={fromGemini ? <StatusChip kind="info">suggested, unverified</StatusChip> : undefined}
        error={problems["interval_days"] ?? (every !== "" && problem ? problem : undefined)}
      />
      <Input
        label="First inspection due"
        type="date"
        value={firstDue}
        onChange={(event) => setDue(event.target.value)}
        error={problems["first_due"]}
      />
      {general ? (
        <p role="alert" className="form-failure">
          {general}
        </p>
      ) : null}
      <div className="sheet-actions">
        {problem ? (
          <Button type="submit" disabled disabledReason={problem}>
            Save plan
          </Button>
        ) : (
          <Button type="submit" loading={saving}>
            Save plan
          </Button>
        )}
        {canCancel ? (
          <Button variant="ghost" onClick={onDone}>
            Cancel
          </Button>
        ) : null}
      </div>
    </form>
  );
}

/** Past inspections, newest first; a worn or defective latest result offers Mark discarded. */
function Inspections({ item }: { item: ItemDetail }) {
  const list = useInspections(item.public_id);
  const refresh = useRefreshInventory();
  const toast = useToast();
  const [busy, setBusy] = useState(false);
  const [failure, setFailure] = useState<string | null>(null);

  if (list.isPending) return <Skeleton height={44} />;
  if (list.isError) {
    return <ErrorState message={list.error.message} onRetry={() => void list.refetch()} />;
  }
  const rows = list.data.items;
  if (rows.length === 0) return <p className="section-note">No inspections recorded yet.</p>;
  const latest = rows[0]!;
  const finding = item.state === "active" && latest.result !== "ok";

  async function discard() {
    if (busy) return;
    setBusy(true);
    setFailure(null);
    try {
      const { event_id } = await api.discard(item.public_id);
      await refresh();
      toast({
        message: `${item.name} discarded.`,
        actionLabel: "Undo",
        onAction: () => void api.undo(event_id).then(refresh),
      });
    } catch (error) {
      setFailure(error instanceof Error ? error.message : "Not discarded.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="tight-stack">
      {finding ? (
        <InnerPanel className="item-banner">
          <span>Inspection suggested: {RESULT_WORDS[latest.result].toLowerCase()}.</span>
          <Button variant="secondary" loading={busy} onClick={() => void discard()}>
            Mark discarded
          </Button>
        </InnerPanel>
      ) : null}
      {failure ? (
        <p role="alert" className="form-failure">
          {failure}
        </p>
      ) : null}
      <span className="field__label">Inspections</span>
      <ol className="history__list">
        {rows.map((row) => (
          <li key={row.id}>
            <span>
              {RESULT_WORDS[row.result]}
              {row.note ? ` · ${row.note}` : ""}
            </span>
            <span className="section-note">{formatDay(row.local_date)}</span>
          </li>
        ))}
      </ol>
    </div>
  );
}
