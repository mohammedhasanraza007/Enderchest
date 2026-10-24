import { useEffect, useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { api } from "../api/endpoints";
import type { NotificationStatus } from "../api/endpoints";
import { keys, useNotifications } from "../api/queries";
import { usePageTitle } from "../hooks/usePageTitle";
import { browserPermission } from "../lib/notifications";
import type { BrowserPermission } from "../lib/notifications";
import { ErrorState } from "../patterns/ErrorState";
import { ReminderList } from "../patterns/Reminders";
import { Button } from "../primitives/Button";
import { Chip } from "../primitives/Chip";
import { GlassCard, InnerPanel } from "../primitives/Glass";
import { Skeleton } from "../primitives/Skeleton";

// P-11, the notification centre: Open / Snoozed / Resolved. Opening the page marks every open
// row read; the rows and their actions are the dashboard's Needs attention rows. A banner offers
// browser notifications while they are not allowed.

const TABS: Array<{ status: NotificationStatus; label: string; empty: string }> = [
  { status: "open", label: "Open", empty: "Nothing needs you right now." },
  { status: "snoozed", label: "Snoozed", empty: "Nothing is snoozed." },
  { status: "resolved", label: "Resolved", empty: "Nothing resolved yet." },
];

export function Notifications() {
  usePageTitle("Notifications");
  const client = useQueryClient();
  const [status, setStatus] = useState<NotificationStatus>("open");
  const list = useNotifications(status);
  const tab = TABS.find((entry) => entry.status === status) ?? TABS[0]!;

  useEffect(() => {
    void api.readAll().then(() => client.invalidateQueries({ queryKey: keys.notificationCount }));
  }, [client]);

  return (
    <div className="notifications-page">
      <div className="page-head">
        <h1 className="page-title">Notifications</h1>
      </div>
      <PermissionBanner />
      <GlassCard>
        <div className="stack">
          <div className="chip-row" role="radiogroup" aria-label="Show">
            {TABS.map((entry) => (
              <Chip
                key={entry.status}
                role="radio"
                selected={status === entry.status}
                onSelect={() => setStatus(entry.status)}
              >
                {entry.label}
              </Chip>
            ))}
          </div>
          {list.isPending ? (
            <div className="stack" aria-busy="true">
              <Skeleton height={72} />
              <Skeleton height={72} />
            </div>
          ) : list.isError ? (
            <ErrorState message={list.error.message} onRetry={() => void list.refetch()} />
          ) : list.data.items.length === 0 ? (
            <div className="empty-state">
              <p>{tab.empty}</p>
            </div>
          ) : (
            <InnerPanel>
              <ReminderList
                rows={list.data.items}
                onOpen={(row) => {
                  if (row.read_at === null) void api.readNotification(row.id);
                }}
              />
            </InnerPanel>
          )}
        </div>
      </GlassCard>
    </div>
  );
}

/** Shown while browser notifications are not allowed and could be. */
function PermissionBanner() {
  const [permission, setPermission] = useState<BrowserPermission>(browserPermission);
  if (permission !== "default") return null;
  return (
    <InnerPanel className="item-banner notifications-page__banner">
      <span>
        Get a browser notification when something needs you. It works while an Enderchest tab is
        open.
      </span>
      <Button
        variant="secondary"
        onClick={() =>
          void window.Notification.requestPermission().then(() =>
            setPermission(browserPermission()),
          )
        }
      >
        Allow browser notifications
      </Button>
    </InnerPanel>
  );
}
