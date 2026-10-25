import { useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { ApiError } from "../../api/client";
import { api } from "../../api/endpoints";
import { keys, useSettings } from "../../api/queries";
import { ErrorState } from "../../patterns/ErrorState";
import { GlassCard } from "../../primitives/Glass";
import { Skeleton } from "../../primitives/Skeleton";
import { Toggle } from "../../primitives/Toggle";
import { useToast } from "../../primitives/Toast";

// Settings, Camera coach (PAGES.md P-02, Phase 7): the `coach_enabled` switch. Off means no tips
// on the camera and no frame sent to be read. The page says what reading a frame means: it
// happens on this computer and nothing is kept.

export function CoachSection() {
  const settings = useSettings();
  return (
    <GlassCard title="Camera coach">
      <div className="stack">
        <p>
          Short tips on the live camera, such as &ldquo;Hold steady&rdquo; or &ldquo;Move a little
          closer to the label&rdquo;. About once a second a small frame is read on this computer; it
          is never saved and never leaves this computer. Taking a photo never waits for a tip.
        </p>
        {settings.isPending ? (
          <Skeleton height={44} />
        ) : settings.isError ? (
          <ErrorState message={settings.error.message} onRetry={() => void settings.refetch()} />
        ) : (
          <CoachToggle on={settings.data.coach_enabled} />
        )}
      </div>
    </GlassCard>
  );
}

function CoachToggle({ on }: { on: boolean }) {
  const client = useQueryClient();
  const toast = useToast();
  const [saving, setSaving] = useState(false);
  const [failure, setFailure] = useState<string | null>(null);

  async function change(next: boolean) {
    setSaving(true);
    setFailure(null);
    try {
      const saved = await api.patchSettings({ coach_enabled: next });
      client.setQueryData(keys.settings, saved);
      toast({ message: next ? "Camera tips are on." : "Camera tips are off." });
    } catch (error) {
      setFailure(error instanceof ApiError ? error.message : "The setting was not saved.");
    } finally {
      setSaving(false);
    }
  }

  return (
    <>
      <Toggle
        label="Show camera tips"
        checked={on}
        disabled={saving}
        disabledReason="Saving…"
        onChange={(next) => void change(next)}
      />
      {failure ? (
        <p role="alert" className="form-failure">
          {failure}
        </p>
      ) : null}
    </>
  );
}
