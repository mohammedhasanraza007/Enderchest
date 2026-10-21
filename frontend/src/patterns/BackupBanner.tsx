import { useBackups, useMakeBackup } from "../api/queries";
import { useSingleFlight } from "../hooks/useSingleFlight";
import { bannerText } from "../lib/backupText";
import type { BannerText } from "../lib/backupText";
import { Button } from "../primitives/Button";
import { StatusChip } from "../primitives/StatusChip";
import { useToast } from "../primitives/Toast";

// The banner under the nav capsule on every page whenever the backup status is not ok
// (DATA_SAFETY.md 7). It says what happened and what to do; when a backup could help, the
// button is right here.

/** The banner itself, without any data loading, so it can be shown in every variant. */
export function BannerView({
  banner,
  busy,
  onBackUp,
}: {
  banner: BannerText;
  busy: boolean;
  onBackUp: () => void;
}) {
  return (
    <div className="banner" role="status">
      <StatusChip kind={banner.severity === "danger" ? "danger" : "warning"}>
        {banner.word}
      </StatusChip>
      <p className="banner__message">{banner.message}</p>
      {banner.canBackUp ? (
        <Button variant="secondary" loading={busy} onClick={onBackUp}>
          Back up now
        </Button>
      ) : null}
    </div>
  );
}

export function BackupBanner() {
  const backups = useBackups();
  const makeBackup = useMakeBackup();
  const toast = useToast();
  const once = useSingleFlight();
  const banner = bannerText(backups.data);
  if (banner === null) return null;

  return (
    <BannerView
      banner={banner}
      busy={makeBackup.isPending}
      onBackUp={() =>
        once((done) =>
          makeBackup.mutate(undefined, {
            onSuccess: () => toast({ message: "Backup saved." }),
            onError: (error) => toast({ message: error.message }),
            onSettled: done,
          }),
        )
      }
    />
  );
}
