import { useEffect, useRef } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";
import { Bell as BellIcon } from "lucide-react";
import { api } from "../api/endpoints";
import type { NotificationView } from "../api/endpoints";
import { useNotificationCount } from "../api/queries";
import { browserPermission, rowName } from "../lib/notifications";
import { setOpenCount } from "../lib/title";

// The bell (DESIGN.md 6.5) and the live part of P-11: the open count is read every 60 s and on
// focus; it badges the bell and the tab title; a row never shown before becomes one browser
// notification, but only after this tab claims it, so two tabs and a reload never show it twice
// (D-107). Browser notifications only work while an Enderchest tab is open (said in Settings).

const ALERTS_PER_POLL = 3;

export function Bell() {
  const count = useNotificationCount();
  const { pathname } = useLocation();
  const open = count.data?.open ?? 0;
  const here = pathname === "/notifications";
  const label = open > 0 ? `Notifications, ${open} open` : "Notifications";
  return (
    <Link
      to="/notifications"
      className={["bell", here ? "is-active" : ""].filter(Boolean).join(" ")}
      aria-label={label}
      aria-current={here ? "page" : undefined}
    >
      <BellIcon size={22} strokeWidth={1.5} aria-hidden="true" />
      {open > 0 ? (
        <span className="bell__badge" aria-hidden="true">
          {open > 99 ? "99+" : open}
        </span>
      ) : null}
    </Link>
  );
}

/** Mounted once in the shell: keeps the tab title and the browser notifications current. */
export function NotificationsLive() {
  const count = useNotificationCount();
  const navigate = useNavigate();
  const asked = useRef(new Set<number>());

  const open = count.data?.open ?? 0;
  useEffect(() => setOpenCount(open), [open]);
  useEffect(() => () => setOpenCount(0), []);

  const unshown = count.data?.unshown;
  useEffect(() => {
    if (!unshown || browserPermission() !== "granted") return;
    const fresh = unshown.filter((row) => !asked.current.has(row.id)).slice(0, ALERTS_PER_POLL);
    for (const row of fresh) {
      asked.current.add(row.id);
      void api.shown(row.id).then(
        ({ claimed }) => {
          if (claimed) show(row, () => navigate("/notifications"));
        },
        () => asked.current.delete(row.id), // not claimed: try again on the next poll
      );
    }
  }, [unshown, navigate]);

  return null;
}

function show(row: NotificationView, onClick: () => void): void {
  const word = row.word.charAt(0).toUpperCase() + row.word.slice(1);
  // The tag is the row id: even if two alerts were made, the system shows one.
  const alert = new window.Notification(rowName(row), {
    body: word,
    tag: `enderchest-${row.id}`,
  });
  alert.onclick = () => {
    window.focus();
    onClick();
    alert.close();
  };
}
