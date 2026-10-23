import { useState } from "react";
import type { FormEvent } from "react";
import { Navigate } from "react-router-dom";
import { useQueryClient } from "@tanstack/react-query";
import { ApiError, fieldProblems } from "../api/client";
import { api } from "../api/endpoints";
import { keys, useProfile, useSaveProfile } from "../api/queries";
import { usePageTitle } from "../hooks/usePageTitle";
import { useSingleFlight } from "../hooks/useSingleFlight";
import { dayPart, localHour } from "../lib/format";
import { browserTimeZone, timeZoneOptions } from "../lib/timezones";
import { Button, LinkButton } from "../primitives/Button";
import { Chip } from "../primitives/Chip";
import { GlassCard } from "../primitives/Glass";
import { BrandMark } from "../primitives/BrandMark";
import { Input, Select } from "../primitives/Input";

// P-01, the first-run screen (PAGES.md). Step 1 asks for a name and a time zone and saves them.
// Step 2 offers six starter categories, all optional. The last step greets the owner and offers
// the one real thing to do next. The server remembers the step (D-093), so closing the tab on
// step 2 and coming back resumes at step 2.

const NAME_ERROR = "Enter a name of 1 to 40 characters.";

// DATA_MODEL 2.4: created only when ticked here, never seeded.
const STARTERS = [
  { name: "Tools", expires_default: false, maintenance_default: true, label_default: true },
  { name: "Electronics", expires_default: false, maintenance_default: true, label_default: true },
  {
    name: "Food and drink",
    expires_default: true,
    maintenance_default: false,
    label_default: false,
  },
  { name: "Cosmetics", expires_default: true, maintenance_default: false, label_default: false },
  { name: "Household", expires_default: false, maintenance_default: false, label_default: true },
  { name: "Other", expires_default: false, maintenance_default: false, label_default: true },
];

export function Welcome() {
  usePageTitle();
  const profile = useProfile();
  const save = useSaveProfile();
  const once = useSingleFlight();
  // Decided once, on arrival: saving the name below must not bounce this page away mid-way.
  const [alreadyDone] = useState(() => profile.data?.first_run_complete ?? false);
  const [step, setStep] = useState<"name" | "categories" | "done">(() =>
    profile.data?.first_run_step === "categories" ? "categories" : "name",
  );
  const [name, setName] = useState("");
  const [timeZone, setTimeZone] = useState(browserTimeZone());
  const [problems, setProblems] = useState<Record<string, string>>({});
  const [failure, setFailure] = useState<string | null>(null);

  if (alreadyDone) return <Navigate to="/" replace />;

  function submit(event: FormEvent) {
    event.preventDefault();
    const trimmed = name.trim();
    if (trimmed.length < 1 || trimmed.length > 40) {
      setProblems({ name: NAME_ERROR });
      return;
    }
    setProblems({});
    setFailure(null);
    once((done) =>
      save.mutate(
        { name: trimmed, timezone: timeZone },
        {
          onSuccess: () => setStep("categories"),
          onError: (error) => {
            const found = fieldProblems(error);
            setProblems(found);
            if (Object.keys(found).length === 0) setFailure(error.message);
          },
          onSettled: done,
        },
      ),
    );
  }

  const savedName = profile.data?.name ?? name.trim();
  return (
    <main className="page page--narrow center-card">
      <BrandMark size={72} />
      <GlassCard className="welcome-card">
        {step === "name" ? (
          <form className="stack" onSubmit={submit} noValidate>
            <h1 className="welcome-card__title">Welcome to Enderchest</h1>
            <p className="welcome-card__intro">
              Tell it your name and time zone. Both stay on this computer.
            </p>
            <Input
              label="Your name"
              autoComplete="given-name"
              autoFocus
              value={name}
              onChange={(event) => setName(event.target.value)}
              error={problems["name"]}
            />
            <Select
              label="Time zone"
              value={timeZone}
              onChange={(event) => setTimeZone(event.target.value)}
              options={timeZoneOptions(timeZone)}
              error={problems["timezone"]}
            />
            {failure ? (
              <p role="alert" className="form-failure">
                {failure}
              </p>
            ) : null}
            <Button type="submit" loading={save.isPending}>
              Continue
            </Button>
          </form>
        ) : step === "categories" ? (
          <StarterCategories onDone={() => setStep("done")} />
        ) : (
          <div className="stack">
            <h1 className="welcome-card__title">
              Good {dayPart(localHour(profile.data?.timezone ?? timeZone))}, {savedName}
            </h1>
            <p className="welcome-card__intro">
              You are set up. Everything stays on this computer.
            </p>
            <LinkButton to="/camera?mode=add">Add your first item</LinkButton>
          </div>
        )}
      </GlassCard>
    </main>
  );
}

/** Step 2: tick any starter categories; Continue makes them, Skip makes none. */
function StarterCategories({ onDone }: { onDone: () => void }) {
  const client = useQueryClient();
  const [ticked, setTicked] = useState<Set<string>>(new Set());
  const [busy, setBusy] = useState(false);
  const [failure, setFailure] = useState<string | null>(null);

  async function finish(names: Set<string>) {
    if (busy) return;
    setBusy(true);
    setFailure(null);
    try {
      for (const starter of STARTERS.filter((s) => names.has(s.name))) {
        try {
          await api.createCategory(starter);
        } catch (error) {
          // Already made on an earlier try (the tab was closed half way): that is fine.
          if (!(error instanceof ApiError && error.code === "conflict")) throw error;
        }
      }
      await api.patchSettings({ first_run_step: "done" });
      await client.invalidateQueries({ queryKey: keys.profile });
      await client.invalidateQueries({ queryKey: keys.categories });
      onDone();
    } catch (error) {
      setFailure(error instanceof Error ? error.message : "Something went wrong.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="stack">
      <h1 className="welcome-card__title">Start with some categories?</h1>
      <p className="welcome-card__intro">
        Tick the ones you want. Each sets sensible defaults, such as an expiry date for food. You
        can change or add categories later in Settings.
      </p>
      <div className="chip-row">
        {STARTERS.map((starter) => (
          <Chip
            key={starter.name}
            selected={ticked.has(starter.name)}
            onSelect={() => {
              const next = new Set(ticked);
              if (next.has(starter.name)) next.delete(starter.name);
              else next.add(starter.name);
              setTicked(next);
            }}
          >
            {starter.name}
          </Chip>
        ))}
      </div>
      {failure ? (
        <p role="alert" className="form-failure">
          {failure}
        </p>
      ) : null}
      <div className="sheet-actions">
        <Button loading={busy} onClick={() => void finish(ticked)}>
          Continue
        </Button>
        <Button variant="ghost" onClick={() => void finish(new Set())}>
          Skip
        </Button>
      </div>
    </div>
  );
}
