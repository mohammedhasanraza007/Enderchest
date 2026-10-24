import { Navigate, Outlet, Route, Routes, useLocation } from "react-router-dom";
import { useProfile } from "./api/queries";
import { AppShell } from "./patterns/AppShell";
import { ErrorState } from "./patterns/ErrorState";
import { BrandMark } from "./primitives/BrandMark";
import { GlassCard } from "./primitives/Glass";
import { Skeleton } from "./primitives/Skeleton";
import { AddQueue } from "./screens/AddQueue";
import { Camera } from "./screens/Camera";
import { ConfirmDraft } from "./screens/ConfirmDraft";
import { Dashboard } from "./screens/Dashboard";
import { Inventory } from "./screens/Inventory";
import { Item } from "./screens/Item";
import { Labels } from "./screens/Labels";
import { NotFound } from "./screens/NotFound";
import { Notifications } from "./screens/Notifications";
import { Settings } from "./screens/Settings";
import { Tasks } from "./screens/Tasks";
import { Trash } from "./screens/Trash";
import { Welcome } from "./screens/Welcome";

// Every route of the app (PAGES.md 1). After Phase 5: first run, the dashboard at `/`,
// Inventory, Item, Camera, the review queue and confirm, Labels, Trash, Tasks, Notifications,
// Settings and the not-found card.

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
          <Route index element={<Dashboard />} />
          <Route path="/inventory" element={<Inventory />} />
          <Route path="/items/:publicId" element={<Item />} />
          <Route path="/camera" element={<Camera />} />
          <Route path="/add" element={<AddQueue />} />
          <Route path="/add/:draftId" element={<ConfirmDraft />} />
          <Route path="/labels" element={<Labels />} />
          <Route path="/trash" element={<Trash />} />
          <Route path="/tasks" element={<Tasks />} />
          <Route path="/notifications" element={<Notifications />} />
          <Route path="/settings" element={<Settings />} />
          <Route path="*" element={<NotFound />} />
        </Route>
      </Route>
    </Routes>
  );
}
