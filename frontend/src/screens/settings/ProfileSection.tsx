import { useState } from "react";
import type { FormEvent } from "react";
import { fieldProblems } from "../../api/client";
import type { Profile } from "../../api/endpoints";
import { useSaveProfile } from "../../api/queries";
import { useSingleFlight } from "../../hooks/useSingleFlight";
import { browserTimeZone, timeZoneOptions } from "../../lib/timezones";
import { Button } from "../../primitives/Button";
import { GlassCard, InnerPanel } from "../../primitives/Glass";
import { Input, Select } from "../../primitives/Input";
import { useToast } from "../../primitives/Toast";

// Settings, Profile (PAGES.md P-02): name and time zone, saved with PUT /profile. If the browser
// is in a different time zone, an offer to switch appears.

export function ProfileSection({ profile }: { profile: Profile }) {
  const save = useSaveProfile();
  const toast = useToast();
  const once = useSingleFlight();
  const [name, setName] = useState(profile.name ?? "");
  const [timeZone, setTimeZone] = useState(profile.timezone);
  const [problems, setProblems] = useState<Record<string, string>>({});
  const [failure, setFailure] = useState<string | null>(null);

  const changed = name.trim() !== (profile.name ?? "") || timeZone !== profile.timezone;
  const browserZone = browserTimeZone();
  const offerBrowserZone = browserZone !== profile.timezone && timeZone !== browserZone;

  function submit(event: FormEvent) {
    event.preventDefault();
    store(timeZone);
  }

  function store(timezone: string) {
    setProblems({});
    setFailure(null);
    once((done) =>
      save.mutate(
        { name, timezone },
        {
          onSuccess: (saved) => {
            setName(saved.name ?? "");
            toast({ message: "Profile saved." });
          },
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

  return (
    <GlassCard title="Profile">
      <form className="stack" onSubmit={submit} noValidate>
        <Input
          label="Your name"
          autoComplete="given-name"
          value={name}
          onChange={(event) => {
            setName(event.target.value);
            setProblems({});
          }}
          error={problems["name"]}
        />
        <Select
          label="Time zone"
          value={timeZone}
          onChange={(event) => {
            setTimeZone(event.target.value);
            setProblems({});
          }}
          options={timeZoneOptions(timeZone)}
          error={problems["timezone"]}
        />
        {offerBrowserZone ? (
          <InnerPanel className="zone-offer">
            <p>
              Your browser says you are in {browserZone}, but Enderchest is set to{" "}
              {profile.timezone}.
            </p>
            {/* Saves at once: the banner goes away, so nothing would say Save is still needed. */}
            <Button
              variant="secondary"
              onClick={() => {
                setTimeZone(browserZone);
                store(browserZone);
              }}
            >
              Use {browserZone}
            </Button>
          </InnerPanel>
        ) : null}
        {failure ? (
          <p role="alert" className="form-failure">
            {failure}
          </p>
        ) : null}
        <div>
          {changed ? (
            <Button type="submit" loading={save.isPending}>
              Save
            </Button>
          ) : (
            <Button type="submit" disabled disabledReason="Change your name or time zone to save.">
              Save
            </Button>
          )}
        </div>
      </form>
    </GlassCard>
  );
}
