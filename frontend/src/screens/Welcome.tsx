import { useState } from "react";
import type { FormEvent } from "react";
import { Navigate } from "react-router-dom";
import { fieldProblems } from "../api/client";
import { useProfile, useSaveProfile } from "../api/queries";
import { usePageTitle } from "../hooks/usePageTitle";
import { useSingleFlight } from "../hooks/useSingleFlight";
import { dayPart, localHour } from "../lib/format";
import { browserTimeZone, timeZoneOptions } from "../lib/timezones";
import { Button, LinkButton } from "../primitives/Button";
import { GlassCard } from "../primitives/Glass";
import { BrandMark } from "../primitives/BrandMark";
import { Input, Select } from "../primitives/Input";

// P-01, the first-run screen (PAGES.md). Step 1 asks for a name and a time zone and saves them.
// Step 2 (starter categories) arrives with categories in Phase 2. The last step greets the owner
// and offers the one real thing to do next. First run counts as complete once a name is saved
// (D-084), so closing the tab after step 1 and coming back goes straight to the app.

const NAME_ERROR = "Enter a name of 1 to 40 characters.";

export function Welcome() {
  usePageTitle();
  const profile = useProfile();
  const save = useSaveProfile();
  const once = useSingleFlight();
  // Decided once, on arrival: saving the name below must not bounce this page away mid-way.
  const [alreadyDone] = useState(() => profile.data?.first_run_complete ?? false);
  const [step, setStep] = useState<"name" | "done">("name");
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
          onSuccess: () => setStep("done"),
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
        ) : (
          <div className="stack">
            <h1 className="welcome-card__title">
              Good {dayPart(localHour(profile.data?.timezone ?? timeZone))}, {savedName}
            </h1>
            <p className="welcome-card__intro">
              You are set up. Everything stays on this computer.
            </p>
            <LinkButton to="/settings">Open settings</LinkButton>
          </div>
        )}
      </GlassCard>
    </main>
  );
}
