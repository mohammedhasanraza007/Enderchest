import { Navigate, Outlet, Route, Routes, useLocation } from "react-router-dom";
import { useProfile } from "./api/queries";
import { AppShell } from "./patterns/AppShell";
import { ErrorState } from "./patterns/ErrorState";
import { BrandMark } from "./primitives/BrandMark";
import { GlassCard } from "./primitives/Glass";
import { Skeleton } from "./primitives/Skeleton";
import { NotFound } from "./screens/NotFound";
import { Settings } from "./screens/Settings";
import { Welcome } from "./screens/Welcome";

// Every route of the app (PAGES.md 1). After this phase that is the first-run screen, Settings
// and the not-found card; `/` goes to Settings until the dashboard exists.

/**
 * Loads the profile once for every page and sends a first-time owner to /welcome. Everything
 * else waits for the profile, so no screen ever flashes with a missing name.
 */
function FirstRunGate() {
  const profile = useProfile();
  const location = useLocation();

  if (profile.isPending) {
    return (
      <main className="page page--narrow center-card" aria-busy="true">
        <BrandMark size={72} />
        <GlassCard>
          <div className="stack">
            <Skeleton width="70%" height={28} />
            <Skeleton />
            <Skeleton width="40%" height={38} />
          </div>
        </GlassCard>
      </main>
    );
  }
  if (profile.isError) {
    return (
      <main className="page page--narrow center-card">
        <BrandMark size={72} />
        <GlassCard title="Enderchest is not answering" headingLevel={1}>
          <ErrorState message={profile.error.message} onRetry={() => void profile.refetch()} />
        </GlassCard>
      </main>
    );
  }
  if (!profile.data.first_run_complete && location.pathname !== "/welcome") {
    return <Navigate to="/welcome" replace />;
  }
  return <Outlet />;
}

export function AppRoutes() {
  return (
    <Routes>
      <Route element={<FirstRunGate />}>
        <Route path="/welcome" element={<Welcome />} />
        <Route element={<AppShell />}>
          <Route index element={<Navigate to="/settings" replace />} />
          <Route path="/settings" element={<Settings />} />
          <Route path="*" element={<NotFound />} />
        </Route>
      </Route>
    </Routes>
  );
}
