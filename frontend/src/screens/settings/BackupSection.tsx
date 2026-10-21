import type { BackupsView } from "../../api/endpoints";
import { useBackups, useMakeBackup } from "../../api/queries";
import { useSingleFlight } from "../../hooks/useSingleFlight";
import { describeBackup, statusLine } from "../../lib/backupText";
import { formatBytes } from "../../lib/format";
import { ErrorState } from "../../patterns/ErrorState";
import { Button } from "../../primitives/Button";
import { GlassCard } from "../../primitives/Glass";
import { Skeleton } from "../../primitives/Skeleton";
import { StatusChip } from "../../primitives/StatusChip";
import type { StatusKind } from "../../primitives/StatusChip";
import { useToast } from "../../primitives/Toast";

// Settings, Backup (PAGES.md P-02, DATA_SAFETY.md 7): the status line, warnings, recent backups,
// the folder, and Back up now. Everything shown here is read from GET /backups.

const RECENT = 8;

function chipFor(view: BackupsView): { kind: StatusKind; word: string } {
  // "Working" is claimed only when a good backup exists; before the first one it says "New".
  if (view.status === "ok") {
    return view.last_good ? { kind: "success", word: "Working" } : { kind: "info", word: "New" };
  }
  if (view.status === "stale") return { kind: "warning", word: "Old" };
  return { kind: "danger", word: view.status === "failing" ? "Failing" : "Not connected" };
}

export function BackupSection({ timeZone }: { timeZone: string }) {
  const backups = useBackups();
  const makeBackup = useMakeBackup();
  const toast = useToast();
  const once = useSingleFlight();

  if (backups.isPending) {
    return (
      <GlassCard title="Backup" aria-busy="true">
        <div className="stack">
          <Skeleton width="60%" />
          <Skeleton width="80%" />
          <Skeleton width="40%" height={38} />
        </div>
      </GlassCard>
    );
  }
  if (backups.isError) {
    return (
      <GlassCard title="Backup">
        <ErrorState message={backups.error.message} onRetry={() => void backups.refetch()} />
      </GlassCard>
    );
  }

  const view = backups.data;
  const chip = chipFor(view);
  return (
    <GlassCard title="Backup">
      <div className="stack">
        <p className="backup-status">
          <StatusChip kind={chip.kind}>{chip.word}</StatusChip>
          <span>{statusLine(view, timeZone)}</span>
        </p>
        {view.last_good ? (
          <p className="section-note">
            Newest good backup: {formatBytes(view.last_good.bytes)}. It was checked when it was
            made.
          </p>
        ) : (
          <p className="section-note">
            Enderchest makes the first one when it starts, and more after changes.
          </p>
        )}
        {view.warnings.map((warning) => (
          <p key={warning} className="backup-warning">
            {warning}
          </p>
        ))}
        <p className="section-note">Folder: {view.folder_hint}</p>
        {view.items.length > 0 ? (
          <ul className="backup-list" aria-label="Recent backups">
            {view.items.slice(0, RECENT).map((item) => (
              <li key={item.name}>{describeBackup(item, timeZone)}</li>
            ))}
          </ul>
        ) : null}
        <div>
          {view.status === "unavailable" ? (
            <Button disabled disabledReason="The backup folder is not connected.">
              Back up now
            </Button>
          ) : (
            <Button
              loading={makeBackup.isPending}
              onClick={() =>
                once((done) =>
                  makeBackup.mutate(undefined, {
                    onSuccess: (made) =>
                      toast({ message: `Backup saved (${formatBytes(made.bytes)}).` }),
                    onError: (error) => toast({ message: error.message }),
                    onSettled: done,
                  }),
                )
              }
            >
              Back up now
            </Button>
          )}
        </div>
      </div>
    </GlassCard>
  );
}
