import { useState } from "react";
import { fileUrl } from "../api/endpoints";
import type { ExpiryView } from "../api/endpoints";
import { StatusChip } from "../primitives/StatusChip";
import type { StatusKind } from "../primitives/StatusChip";

// Small pieces every item screen shares: the photo (thumb in lists, file on detail) with a calm
// fallback, and the expiry status chip (PAGES.md 2, DATA_MODEL 3.2).

/** A photo, or a neutral tile with the item's initial when there is none or it fails to load. */
export function ItemPhoto({
  photoId,
  name,
  size = "thumb",
  className,
}: {
  photoId: string | null;
  name: string;
  size?: "thumb" | "file";
  className?: string;
}) {
  const [broken, setBroken] = useState(false);
  const classes = ["item-photo", className ?? ""].filter(Boolean).join(" ");
  if (photoId === null || broken) {
    return (
      <div className={`${classes} item-photo--empty`} aria-hidden="true">
        {name.trim().charAt(0).toUpperCase() || "?"}
      </div>
    );
  }
  return (
    <img
      className={classes}
      src={size === "thumb" ? fileUrl.thumb(photoId) : fileUrl.photo(photoId)}
      alt=""
      loading="lazy"
      decoding="async"
      onError={() => setBroken(true)}
    />
  );
}

const KIND: Partial<Record<ExpiryView["status"], StatusKind>> = {
  expired: "danger",
  today: "warning",
  soon: "warning",
};

/**
 * Lists show only an expiry that needs attention; the item page also shows "N days left",
 * "no expiry" and "date not set" (DATA_MODEL 3.2).
 */
export function ExpiryChip({ expiry, always = false }: { expiry: ExpiryView; always?: boolean }) {
  const kind = KIND[expiry.status];
  if (kind) return <StatusChip kind={kind}>{expiry.word}</StatusChip>;
  if (!always) return null;
  return <StatusChip kind={expiry.status === "ok" ? "success" : "info"}>{expiry.word}</StatusChip>;
}

const STATE_WORD = { used: "used", expired: "marked expired", discarded: "discarded" } as const;

/** Items that are not active say so; active items show nothing here. */
export function StateChip({ state }: { state: "active" | "used" | "expired" | "discarded" }) {
  if (state === "active") return null;
  return <StatusChip kind="info">{STATE_WORD[state]}</StatusChip>;
}
