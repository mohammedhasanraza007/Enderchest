import { useState } from "react";
import type { FormEvent } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { api } from "../../api/endpoints";
import { keys, useRefreshInventory, useSettings } from "../../api/queries";
import { useSingleFlight } from "../../hooks/useSingleFlight";
import { splitProblems } from "../../lib/formErrors";
import { browserPermission, PERMISSION_WORDS } from "../../lib/notifications";
import type { BrowserPermission } from "../../lib/notifications";
import { ErrorState } from "../../patterns/ErrorState";
import { Button } from "../../primitives/Button";
import { GlassCard } from "../../primitives/Glass";
import { Input } from "../../primitives/Input";
import { Skeleton } from "../../primitives/Skeleton";
import { useToast } from "../../primitives/Toast";

// Settings, Notifications (PAGES.md P-02): how many days before expiry to warn, the browser's
// permission with a button to allow it, and a real test notification. The honest limit is said
// here: browser notifications need an open Enderchest tab.

export function NotificationsSection() {
  const settings = useSettings();
  return (
    <GlassCard title="Notifications">
      <div className="stack">
        <p>Reminders appear here and as browser notifications while an Enderchest tab is open.</p>
        {settings.isPending ? (
          <Skeleton height={44} />
        ) : settings.isError ? (
          <ErrorState message={settings.error.message} onRetry={() => void settings.refetch()} />
        ) : (
          <LeadDays saved={settings.data.lead_days} />
        )}
        <BrowserNotifications />
      </div>
    </GlassCard>
  );
}

function LeadDays({ saved }: { saved: number }) {
  const client = useQueryClient();
  const refresh = useRefreshInventory();
  const toast = useToast();
  const once = useSingleFlight();
  const [value, setValue] = useState(String(saved));
  const [problem, setProblem] = useState<string | null>(null);
  const [failure, setFailure] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  const days = Number(value);
  const valid = /^\d+$/.test(value.trim()) && days >= 1 && days <= 14;
  const changed = valid && days !== saved;

  function submit(event: FormEvent) {
    event.preventDefault();
    if (!changed) return;
    setFailure(null);
    once((done) => {
      setSaving(true);
      api
        .patchSettings({ lead_days: days })
        .then(async () => {
          // The days decide which items are "expiring soon", so every list is read again.
          await Promise.all([client.invalidateQueries({ queryKey: keys.settings }), refresh()]);
          toast({ message: `You will be warned ${days} ${days === 1 ? "day" : "days"} before.` });
        })
        .catch((error: unknown) => {
          const found = splitProblems(error, ["lead_days"]);
          setProblem(found.fields["lead_days"] ?? null);
          setFailure(found.general);
        })
        .finally(() => {
          setSaving(false);
          done();
        });
    });
  }

  return (
    <form className="lead-days" onSubmit={submit} noValidate>
      <Input
        label="Warn me this many days before expiry"
        inputMode="numeric"
        value={value}
        onChange={(event) => {
          setValue(event.target.value);
          setProblem(null);
        }}
        error={problem ?? (valid || value === "" ? undefined : "Choose 1 to 14 days.")}
      />
      {changed ? (
        <Button type="submit" loading={saving}>
          Save
        </Button>
      ) : (
        <Button
          type="submit"
          disabled
          disabledReason={valid ? "Change the number of days to save." : "Choose 1 to 14 days."}
        >
          Save
        </Button>
      )}
      {failure ? (
        <p role="alert" className="form-failure">
          {failure}
        </p>
      ) : null}
    </form>
  );
}

function BrowserNotifications() {
  const toast = useToast();
  const [permission, setPermission] = useState<BrowserPermission>(browserPermission);

  async function allow() {
    await window.Notification.requestPermission();
    setPermission(browserPermission());
  }

  function test() {
    // A real browser notification, made here in the browser; nothing is sent anywhere.
    new window.Notification("Enderchest", {
      body: "Test notification: reminders look like this.",
      tag: "enderchest-test",
    });
    toast({ message: "Test notification sent to your browser." });
  }

  return (
    <div className="tight-stack">
      <span className="field__label">Browser notifications</span>
      <p className="section-note">{PERMISSION_WORDS[permission]}</p>
      <div className="chip-row">
        {permission === "default" ? (
          <Button variant="secondary" onClick={() => void allow()}>
            Allow browser notifications
          </Button>
        ) : null}
        {permission === "granted" ? (
          <Button variant="secondary" onClick={test}>
            Send a test notification
          </Button>
        ) : (
          <Button
            variant="secondary"
            disabled
            disabledReason={
              permission === "unsupported"
                ? "This browser cannot show notifications."
                : "Allow browser notifications first."
            }
          >
            Send a test notification
          </Button>
        )}
      </div>
    </div>
  );
}
