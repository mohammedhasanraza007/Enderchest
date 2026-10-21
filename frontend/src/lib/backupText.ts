// Plain-language wording for the backup status (DATA_SAFETY.md 7, "Surfacing"; DESIGN.md 12):
// what happened, and what to do. The same words feed the name menu, the banner and Settings.

import type { BackupItem, BackupsView } from "../api/endpoints";
import { formatBytes, formatMoment } from "./format";

export type Severity = "ok" | "warning" | "danger";

/** One short line for the name menu, for example "Last backup 21 Oct, 10:06 pm". */
export function statusLine(view: BackupsView | undefined, timeZone: string): string {
  if (view === undefined) return "Checking backups…";
  if (view.status === "unavailable") return "Backup folder not connected";
  if (view.status === "failing") return "The last two backups failed";
  if (view.status === "stale") return "Last good backup is over 7 days old";
  if (view.last_good === null) return "No backup yet";
  return `Last backup ${formatMoment(view.last_good.at, timeZone)}`;
}

export interface BannerText {
  severity: Severity;
  word: string;
  message: string;
  /** True when "Back up now" can help; false when the folder itself must be fixed first. */
  canBackUp: boolean;
}

/** The banner under the nav capsule for every status except ok (DATA_SAFETY.md 7). */
export function bannerText(view: BackupsView | undefined): BannerText | null {
  if (view === undefined || view.status === "ok") return null;
  if (view.status === "unavailable") {
    return {
      severity: "danger",
      word: "Not backed up",
      message:
        "The backup folder is not connected, so nothing is being backed up. " +
        "Check the folder shown in Settings, then run run.bat again.",
      canBackUp: false,
    };
  }
  if (view.status === "failing") {
    return {
      severity: "danger",
      word: "Backups failing",
      message:
        "The last two backups failed. Your data is safe, but it is not being backed up. " +
        "Try Back up now; if it fails again, check the backup folder.",
      canBackUp: true,
    };
  }
  return {
    severity: "warning",
    word: "Backup is old",
    message: "The last good backup is more than 7 days old. Back up now to make a fresh one.",
    canBackUp: true,
  };
}

const KIND_WORDS: Record<BackupItem["kind"], string> = {
  auto: "automatic",
  manual: "manual",
  "pre-migration": "before an update",
  safety: "safety copy",
};

/** "21 Oct, 10:06 pm, automatic, 44 KB" */
export function describeBackup(item: BackupItem, timeZone: string): string {
  return `${formatMoment(item.at, timeZone)}, ${KIND_WORDS[item.kind]}, ${formatBytes(item.bytes)}`;
}
