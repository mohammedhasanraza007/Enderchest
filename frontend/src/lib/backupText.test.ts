import { describe, expect, it } from "vitest";
import type { BackupItem, BackupsView } from "../api/endpoints";
import { bannerText, describeBackup, statusLine } from "./backupText";

const base: BackupsView = {
  status: "ok",
  last_good: { name: "auto-20261021T160636Z", at: "2026-10-21T16:06:36Z", bytes: 45056 },
  warnings: [],
  items: [],
  folder_hint: "C:/Backups",
};

describe("statusLine", () => {
  it("says it is still checking before the first answer", () => {
    expect(statusLine(undefined, "UTC")).toBe("Checking backups…");
  });
  it("shows the last good backup in the owner's time zone", () => {
    expect(statusLine(base, "Asia/Kolkata")).toBe("Last backup 21 Oct, 9:36 pm");
  });
  it("says so when there is no backup yet", () => {
    expect(statusLine({ ...base, last_good: null }, "UTC")).toBe("No backup yet");
  });
  it("names each problem plainly", () => {
    expect(statusLine({ ...base, status: "unavailable" }, "UTC")).toBe(
      "Backup folder not connected",
    );
    expect(statusLine({ ...base, status: "failing" }, "UTC")).toBe("The last two backups failed");
    expect(statusLine({ ...base, status: "stale" }, "UTC")).toContain("over 7 days");
  });
});

describe("bannerText", () => {
  it("shows no banner while backups are ok or still loading", () => {
    expect(bannerText(base)).toBeNull();
    expect(bannerText(undefined)).toBeNull();
  });
  it("offers Back up now only where a backup could help", () => {
    expect(bannerText({ ...base, status: "unavailable" })?.canBackUp).toBe(false);
    expect(bannerText({ ...base, status: "failing" })?.canBackUp).toBe(true);
    expect(bannerText({ ...base, status: "stale" })?.canBackUp).toBe(true);
  });
  it("says what to do, and rates the folder problem as the more serious", () => {
    const folder = bannerText({ ...base, status: "unavailable" });
    expect(folder?.severity).toBe("danger");
    expect(folder?.message).toContain("run.bat");
    expect(bannerText({ ...base, status: "stale" })?.severity).toBe("warning");
  });
});

describe("describeBackup", () => {
  it("writes the time, the kind in plain words and the size", () => {
    const item: BackupItem = {
      name: "pre-migration-v1-to-v2-20261021T160636Z",
      kind: "pre-migration",
      at: "2026-10-21T16:06:36Z",
      bytes: 45056,
      item_count: null,
      ok: true,
    };
    expect(describeBackup(item, "UTC")).toBe("21 Oct, 4:06 pm, before an update, 44 KB");
  });
});
