import { useState } from "react";
import { Link } from "react-router-dom";
import { api, SAVINGS_SHOWN } from "../api/endpoints";
import type { SavingView, SavingsPeriod } from "../api/endpoints";
import { useRefreshInventory, useSavings } from "../api/queries";
import { usePageTitle } from "../hooks/usePageTitle";
import { formatDay } from "../lib/format";
import { formatRupees } from "../lib/money";
import { ErrorState } from "../patterns/ErrorState";
import { Button } from "../primitives/Button";
import { Chip } from "../primitives/Chip";
import { GlassCard } from "../primitives/Glass";
import { Dialog } from "../primitives/Overlay";
import { Skeleton } from "../primitives/Skeleton";
import { useToast } from "../primitives/Toast";

// P-14, Savings: the rupee total of purchases the owner skipped because they already had the
// item, confirmed one by one with a typed price ("I didn't buy it"). No estimates, ever.

export function Savings() {
  usePageTitle("Savings");
  const [period, setPeriod] = useState<SavingsPeriod>("month");
  const savings = useSavings(period);
  const [removing, setRemoving] = useState<SavingView | null>(null);
  const data = savings.data;

  return (
    <div className="savings-page">
      <h1 className="page-title">Savings</h1>
      <GlassCard className="savings-total">
        <div className="chip-row" role="radiogroup" aria-label="Period">
          <Chip role="radio" selected={period === "month"} onSelect={() => setPeriod("month")}>
            This month
          </Chip>
          <Chip role="radio" selected={period === "all"} onSelect={() => setPeriod("all")}>
            All time
          </Chip>
        </div>
        {data ? (
          <p className="savings-total__amount" aria-live="polite">
            {formatRupees(period === "month" ? data.month_paise : data.total_paise)}
          </p>
        ) : (
          <Skeleton height={72} />
        )}
        <p className="section-note">
          {period === "month" ? "Saved this month" : "Saved since you started"}, counted only from
          purchases you confirmed you skipped.
        </p>
      </GlassCard>
      <GlassCard className="savings-list">
        {savings.isPending ? (
          <div className="stack" aria-busy="true">
            <Skeleton height={56} />
            <Skeleton height={56} />
          </div>
        ) : savings.isError || !data ? (
          <ErrorState
            message={savings.error?.message ?? "The savings could not be read."}
            onRetry={() => void savings.refetch()}
          />
        ) : data.items.length === 0 ? (
          <p className="savings-empty">
            Nothing saved yet. When you skip a purchase because you already own it, it appears here.
          </p>
        ) : (
          <>
            <ul className="row-list">
              {data.items.map((saving) => (
                <li key={saving.id} className="row-list__row">
                  <div className="row-list__text">
                    {saving.item_public_id ? (
                      <Link to={`/items/${saving.item_public_id}`}>{saving.item_name}</Link>
                    ) : (
                      <span>{saving.item_name}</span>
                    )}
                    <span className="section-note">
                      {formatDay(saving.local_date)}
                      {saving.note ? ` · ${saving.note}` : ""}
                    </span>
                  </div>
                  <span className="savings-price">{formatRupees(saving.price_paise)}</span>
                  <Button variant="ghost" onClick={() => setRemoving(saving)}>
                    Remove
                  </Button>
                </li>
              ))}
            </ul>
            {data.next_cursor ? (
              <p className="section-note">
                Showing the newest {SAVINGS_SHOWN}; the total counts every entry.
              </p>
            ) : null}
          </>
        )}
      </GlassCard>
      <RemoveDialog saving={removing} onClose={() => setRemoving(null)} />
    </div>
  );
}

function RemoveDialog({ saving, onClose }: { saving: SavingView | null; onClose: () => void }) {
  const refresh = useRefreshInventory();
  const toast = useToast();
  const [busy, setBusy] = useState(false);
  const [failure, setFailure] = useState<string | null>(null);

  async function remove() {
    if (!saving || busy) return;
    setBusy(true);
    try {
      const done = await api.removeSaving(saving.id);
      await refresh();
      onClose();
      toast({
        message: `Removed ${formatRupees(saving.price_paise)} for ${saving.item_name}.`,
        actionLabel: "Undo",
        onAction: () => void api.undo(done.event_id).then(refresh),
      });
    } catch (error) {
      setFailure(error instanceof Error ? error.message : "It could not be removed.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <Dialog open={saving !== null} onClose={onClose} title="Remove this saving?">
      {saving ? (
        <div className="stack">
          <p>
            {formatRupees(saving.price_paise)} for {saving.item_name} leaves the totals. You can
            undo it for a minute.
          </p>
          {failure ? (
            <p role="alert" className="field__error">
              {failure}
            </p>
          ) : null}
          <div className="chip-row">
            <Button loading={busy} onClick={() => void remove()}>
              Remove
            </Button>
            <Button variant="ghost" onClick={onClose}>
              Keep it
            </Button>
          </div>
        </div>
      ) : null}
    </Dialog>
  );
}
