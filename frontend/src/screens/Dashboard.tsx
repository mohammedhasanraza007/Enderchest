import { useState } from "react";
import type { Dashboard as DashboardData, RingName } from "../api/endpoints";
import { useDashboard } from "../api/queries";
import { usePageTitle } from "../hooks/usePageTitle";
import { greetingWord } from "../lib/dashboard";
import { ErrorState } from "../patterns/ErrorState";
import { HealthRings } from "../patterns/HealthRings";
import { ReminderList } from "../patterns/Reminders";
import { RingSheet } from "../patterns/RingSheet";
import { Road } from "../patterns/Road";
import { LinkButton } from "../primitives/Button";
import { GlassCard, InnerPanel } from "../primitives/Glass";
import { Skeleton } from "../primitives/Skeleton";

// P-12, the dashboard (DESIGN.md 6.7 to 6.11): greeting, health rings, Needs attention and the
// 14-day road, all from one request. Every number on it is the server's (F-020); an empty
// inventory shows the real empty dashboard, never sample data.

const CARD_ROWS = 3;

export function Dashboard() {
  usePageTitle("Dashboard");
  const board = useDashboard();
  const [ring, setRing] = useState<RingName | null>(null);

  if (board.isPending) return <DashboardSkeleton />;
  if (board.isError) {
    return (
      <div className="dashboard">
        <GlassCard title="The dashboard did not load" headingLevel={1}>
          <ErrorState message={board.error.message} onRetry={() => void board.refetch()} />
        </GlassCard>
      </div>
    );
  }
  const data = board.data;
  return (
    <div className="dashboard">
      <div className="dashboard__hero">
        <div className="greeting">
          <h1 className="greeting__title">
            {greetingWord(data.greeting.part)}
            <br />
            {data.greeting.name}
          </h1>
          <p className="greeting__subtitle">{data.subtitle}</p>
        </div>
        <HealthRings board={data} onOpen={setRing} />
        <AttentionCard attention={data.attention} />
      </div>
      <Road
        road={data.road}
        title="Next 14 days"
        emptyText="No tasks or expiries in the next 14 days."
        savings={data.savings}
      />
      <RingSheet ring={ring} rings={data.rings} onChoose={setRing} onClose={() => setRing(null)} />
    </div>
  );
}

/** At most three rows; with more, two rows and "View all N" in the third place (D-113). */
function AttentionCard({ attention }: { attention: DashboardData["attention"] }) {
  const overflow = attention.total > CARD_ROWS;
  const rows = overflow ? attention.rows.slice(0, CARD_ROWS - 1) : attention.rows;
  return (
    <GlassCard className="attention-card" aria-labelledby="attention-title">
      <h2 id="attention-title" className="attention-card__title">
        Needs attention
      </h2>
      <InnerPanel>
        {rows.length === 0 ? (
          <div className="attention-card__empty">
            <p>Nothing needs attention.</p>
            <p className="section-note">Reminders show here when something is due.</p>
          </div>
        ) : (
          <ReminderList rows={rows} />
        )}
        {overflow ? (
          <div className="attention-card__more">
            <LinkButton variant="secondary" to="/notifications">
              View all {attention.total}
            </LinkButton>
          </div>
        ) : null}
      </InnerPanel>
    </GlassCard>
  );
}

/** Shape-matched placeholders while the one request runs (DESIGN.md 13). */
function DashboardSkeleton() {
  return (
    <div className="dashboard" aria-busy="true">
      <div className="dashboard__hero">
        <div className="greeting">
          <Skeleton width="80%" height={56} />
          <Skeleton width="60%" height={56} />
          <Skeleton width="70%" height={20} />
        </div>
        <div className="rings rings--loading">
          <Skeleton width={360} height={360} />
        </div>
        <GlassCard className="attention-card">
          <Skeleton width="50%" height={24} />
          <Skeleton height={180} />
        </GlassCard>
      </div>
      <Skeleton height={27} />
    </div>
  );
}
