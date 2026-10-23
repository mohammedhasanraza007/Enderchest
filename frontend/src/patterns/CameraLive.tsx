import { createContext, useContext, useMemo, useState } from "react";
import type { ReactNode } from "react";

// Whether a camera stream is running right now. The camera page sets it; the nav reads it to show
// the LIVE badge, which must match the real stream state (DESIGN.md 6.4 and 13).

interface CameraLiveState {
  live: boolean;
  setLive: (live: boolean) => void;
}

const CameraLiveContext = createContext<CameraLiveState>({ live: false, setLive: () => {} });

export function CameraLiveProvider({ children }: { children: ReactNode }) {
  const [live, setLive] = useState(false);
  const value = useMemo(() => ({ live, setLive }), [live]);
  return <CameraLiveContext.Provider value={value}>{children}</CameraLiveContext.Provider>;
}

export function useCameraLive(): CameraLiveState {
  return useContext(CameraLiveContext);
}
