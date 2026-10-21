import { useHealth } from "../../api/queries";
import { ErrorState } from "../../patterns/ErrorState";
import { BrandMark } from "../../primitives/BrandMark";
import { GlassCard } from "../../primitives/Glass";
import { Skeleton } from "../../primitives/Skeleton";

// Settings, About (PAGES.md P-02): the logo, the app version, the database version and the
// build date, all from GET /health. A build date that was never recorded says so.

export function AboutSection() {
  const health = useHealth();

  return (
    <GlassCard title="About">
      {health.isPending ? (
        <div className="stack" aria-busy="true">
          <Skeleton width={96} height={96} />
          <Skeleton width="50%" />
        </div>
      ) : health.isError ? (
        <ErrorState message={health.error.message} onRetry={() => void health.refetch()} />
      ) : (
        <div className="about">
          <BrandMark size={96} decorative />
          <dl className="about__list">
            <div>
              <dt>App version</dt>
              <dd>{health.data.app_version}</dd>
            </div>
            <div>
              <dt>Database version</dt>
              <dd>
                {health.data.schema_found ?? "unknown"} of {health.data.schema_supported} supported
              </dd>
            </div>
            <div>
              <dt>Build date</dt>
              <dd>{health.data.build_date ?? "not recorded"}</dd>
            </div>
          </dl>
        </div>
      )}
    </GlassCard>
  );
}
