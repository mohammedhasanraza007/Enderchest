// The component gallery: TEST CODE ONLY. It is built by vite.gallery.config.ts into dist-e2e for
// the browser tests (contrast, rendering in both themes) and is never part of the app bundle.
// The sample values below exist only here; the app never shows invented data.

import "@fontsource-variable/dm-sans";
import "@fontsource-variable/jetbrains-mono";
import "@fontsource-variable/newsreader/opsz.css";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { StrictMode, useState } from "react";
import type { ReactNode } from "react";
import { createRoot } from "react-dom/client";
import { MemoryRouter } from "react-router-dom";
import type { BackupsView, Profile } from "../api/endpoints";
import { keys } from "../api/queries";
import { bannerText } from "../lib/backupText";
import { BannerView } from "../patterns/BackupBanner";
import { NavCapsule } from "../patterns/NavCapsule";
import { BrandMark } from "../primitives/BrandMark";
import { Button, LinkButton } from "../primitives/Button";
import { Chip } from "../primitives/Chip";
import { GlassCard, InnerPanel } from "../primitives/Glass";
import { Input, Select } from "../primitives/Input";
import { LiveBadge } from "../primitives/LiveBadge";
import { Dialog, Sheet } from "../primitives/Overlay";
import { Skeleton } from "../primitives/Skeleton";
import { StatusChip } from "../primitives/StatusChip";
import { ToastProvider, useToast } from "../primitives/Toast";
import { Toggle } from "../primitives/Toggle";
import "../styles/base.css";
import "../primitives/primitives.css";
import "../patterns/patterns.css";
import "../screens/screens.css";
import "./gallery.css";

const SAMPLE_PROFILE: Profile & { name: string } = {
  name: "Sample Name",
  timezone: "Asia/Kolkata",
  theme: "system",
  first_run_complete: true,
};

const SAMPLE_BACKUPS: BackupsView = {
  status: "ok",
  last_good: { name: "auto-20261021T160636Z", at: "2026-10-21T16:06:36Z", bytes: 45056 },
  warnings: [],
  items: [],
  folder_hint: "C:/Users/example/Enderchest-Backups",
};

const client = new QueryClient();
client.setQueryData(keys.backups, SAMPLE_BACKUPS);

const ZONES = [
  { value: "Asia/Kolkata", label: "Asia/Kolkata" },
  { value: "UTC", label: "UTC" },
];

function Section({ title, children }: { title: string; children: ReactNode }) {
  return (
    <section className="gallery__section" aria-label={title}>
      <h2 className="gallery__heading">{title}</h2>
      <div className="gallery__row">{children}</div>
    </section>
  );
}

function Gallery() {
  const toast = useToast();
  const [dialog, setDialog] = useState(false);
  const [sheet, setSheet] = useState(false);
  const [on, setOn] = useState(true);
  const [chip, setChip] = useState("b");

  return (
    <>
      <NavCapsule profile={SAMPLE_PROFILE} />
      <main className="page">
        <h1 className="settings__title">Component gallery</h1>

        <Section title="Banners">
          {(["unavailable", "failing", "stale"] as const).map((status) => {
            const banner = bannerText({ ...SAMPLE_BACKUPS, status });
            return banner ? (
              <BannerView key={status} banner={banner} busy={false} onBackUp={() => undefined} />
            ) : null;
          })}
        </Section>

        <Section title="Buttons">
          <Button>Primary</Button>
          <Button variant="secondary">Secondary</Button>
          <Button variant="ghost">Ghost</Button>
          <Button loading>Loading</Button>
          <Button disabled disabledReason="Nothing to save yet.">
            Disabled
          </Button>
          <LinkButton to="/somewhere" variant="secondary">
            Link button
          </LinkButton>
        </Section>

        <GlassCard title="A frosted card" headingLevel={2}>
          <p>Text on the card uses the full text colour.</p>
          <p className="section-note">Secondary text on glass uses the glass muted colour.</p>
          <InnerPanel>
            <p>One nested inner panel, without blur.</p>
            <p className="section-note">Muted text inside the panel.</p>
          </InnerPanel>
          <div className="stack" style={{ marginTop: 16 }}>
            <Input label="Your name" defaultValue="Mohammed" hint="A hint under the field." />
            <Input
              label="With an error"
              defaultValue=""
              error="Enter a name of 1 to 40 characters."
            />
            <Select label="Time zone" options={ZONES} defaultValue="Asia/Kolkata" />
            <Toggle label="A switch" checked={on} onChange={setOn} />
            <Toggle
              label="A disabled switch"
              checked={false}
              onChange={() => undefined}
              disabled
              disabledReason="Needs a key first."
            />
          </div>
        </GlassCard>

        <Section title="Chips and status">
          <Chip>Plain label</Chip>
          {["a", "b", "c"].map((value) => (
            <Chip
              key={value}
              role="radio"
              selected={chip === value}
              onSelect={() => setChip(value)}
            >
              Choice {value}
            </Chip>
          ))}
          <StatusChip kind="success">Working</StatusChip>
          <StatusChip kind="warning">Old</StatusChip>
          <StatusChip kind="danger">Failing</StatusChip>
          <StatusChip kind="info">Note</StatusChip>
          <LiveBadge />
        </Section>

        <Section title="Overlays and toast">
          <Button variant="secondary" onClick={() => setDialog(true)}>
            Open dialog
          </Button>
          <Button variant="secondary" onClick={() => setSheet(true)}>
            Open sheet
          </Button>
          <Button
            variant="secondary"
            onClick={() =>
              toast({ message: "Saved.", actionLabel: "Undo", onAction: () => undefined })
            }
          >
            Show toast
          </Button>
        </Section>
        <Dialog open={dialog} onClose={() => setDialog(false)} title="A dialog">
          <p>Dialog content on the card material.</p>
        </Dialog>
        <Sheet open={sheet} onClose={() => setSheet(false)} title="A sheet">
          <p>Sheet content on the card material.</p>
        </Sheet>

        <Section title="Skeleton and brand mark">
          <Skeleton width={200} height={24} />
          <BrandMark size={32} decorative />
          <BrandMark size={72} />
          <BrandMark size={96} />
        </Section>

        <Section title="Fonts and the rupee sign">
          <p data-testid="rupee-sans" style={{ fontFamily: "var(--font-sans)", fontSize: 32 }}>
            ₹1,24,500
          </p>
          <p
            data-testid="rupee-display"
            style={{ fontFamily: "var(--font-display)", fontSize: 32 }}
          >
            ₹1,24,500
          </p>
          <p data-testid="rupee-mono" style={{ fontFamily: "var(--font-mono)", fontSize: 32 }}>
            ₹1,24,500
          </p>
        </Section>
      </main>
    </>
  );
}

const root = document.getElementById("root");
if (root === null) throw new Error("gallery.html has no #root element");
createRoot(root).render(
  <StrictMode>
    <MemoryRouter>
      <QueryClientProvider client={client}>
        <ToastProvider>
          <Gallery />
        </ToastProvider>
      </QueryClientProvider>
    </MemoryRouter>
  </StrictMode>,
);
