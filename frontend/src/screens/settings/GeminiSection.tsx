import { useState } from "react";
import type { FormEvent } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { fieldProblems } from "../../api/client";
import { api } from "../../api/endpoints";
import type { GeminiStatus, SettingsPatch } from "../../api/endpoints";
import { keys, useGemini } from "../../api/queries";
import { splitProblems } from "../../lib/formErrors";
import { ErrorState } from "../../patterns/ErrorState";
import { Button } from "../../primitives/Button";
import { Chip } from "../../primitives/Chip";
import { GlassCard } from "../../primitives/Glass";
import { Input } from "../../primitives/Input";
import { Skeleton } from "../../primitives/Skeleton";
import { StatusChip } from "../../primitives/StatusChip";
import { Toggle } from "../../primitives/Toggle";
import { useToast } from "../../primitives/Toast";

// Settings, Gemini (PAGES.md P-02, Phase 3): optional help from Google's Gemini on the confirm
// screen. The key is write-only (the page only ever learns "set" or "not set"); mode, model and
// photo sharing are ordinary settings. The page says plainly what leaves this computer.

const MODES: Array<{ value: GeminiStatus["mode"]; label: string; note: string }> = [
  { value: "off", label: "Off", note: "Gemini is never called." },
  {
    value: "ask",
    label: "Ask each time",
    note: "An Improve with Gemini button appears on the confirm screen.",
  },
  {
    value: "auto",
    label: "Automatic",
    note: "Gemini is asked only when the photo reading found neither a name nor a model.",
  },
];

export function GeminiSection() {
  const gemini = useGemini();
  return (
    <GlassCard title="Gemini">
      <p className="stack-gap section-note">
        Optional. Enderchest reads photos on this computer and works fully without Gemini. When
        Gemini is used, the text read from a photo goes to Google, and the photo itself only if
        "Send photos to Gemini" is on. Its answers are suggestions, marked unverified.
      </p>
      {gemini.isPending ? (
        <Skeleton height={180} />
      ) : gemini.isError ? (
        <ErrorState message={gemini.error.message} onRetry={() => void gemini.refetch()} />
      ) : (
        <GeminiControls status={gemini.data} />
      )}
    </GlassCard>
  );
}

function GeminiControls({ status }: { status: GeminiStatus }) {
  const client = useQueryClient();
  const toast = useToast();
  const [failure, setFailure] = useState<string | null>(null);
  const [busy, setBusy] = useState<string | null>(null);

  async function run(what: string, work: () => Promise<unknown>, done?: string) {
    if (busy) return;
    setBusy(what);
    setFailure(null);
    try {
      await work();
      await Promise.all([
        client.invalidateQueries({ queryKey: keys.gemini }),
        client.invalidateQueries({ queryKey: keys.settings }),
      ]);
      if (done) toast({ message: done });
    } catch (error) {
      setFailure(splitProblems(error, []).general ?? "Something went wrong.");
    } finally {
      setBusy(null);
    }
  }

  const patch = (body: SettingsPatch, done?: string) =>
    void run("settings", () => api.patchSettings(body), done);

  return (
    <div className="stack gemini-settings">
      <div className="gemini-settings__status">
        {status.key_set ? (
          <StatusChip kind="success">Key set</StatusChip>
        ) : (
          <StatusChip kind="info">No key</StatusChip>
        )}
        {status.key_set ? (
          <Button
            variant="ghost"
            loading={busy === "remove"}
            onClick={() => void run("remove", api.removeGeminiKey, "Gemini key removed.")}
          >
            Remove key
          </Button>
        ) : null}
      </div>
      <KeyForm keySet={status.key_set} />

      <fieldset className="stack-gap">
        <legend className="field__label">When to use Gemini</legend>
        <div className="chip-row" role="radiogroup" aria-label="When to use Gemini">
          {MODES.map((mode) => (
            <Chip
              key={mode.value}
              role="radio"
              selected={status.mode === mode.value}
              onSelect={() => patch({ gemini_mode: mode.value })}
            >
              {mode.label}
            </Chip>
          ))}
        </div>
        <p className="section-note">
          {MODES.find((mode) => mode.value === status.mode)?.note}
          {status.mode !== "off" && !status.key_set ? " It needs a key first." : ""}
        </p>
      </fieldset>

      <Toggle
        label="Send photos to Gemini"
        checked={status.share_images}
        onChange={(next) => patch({ share_images_with_gemini: next })}
      />
      <p className="section-note">
        {status.share_images
          ? "On: the photo is sent too, scaled down and without its location or camera details."
          : "Off: only the text read on this computer is sent, never the photo."}
      </p>

      <ModelForm model={status.model} />

      <div className="gemini-settings__test">
        {status.key_set ? (
          <TestButton />
        ) : (
          <Button variant="secondary" disabled disabledReason="Set a key first.">
            Test connection
          </Button>
        )}
      </div>
      {failure ? (
        <p role="alert" className="form-failure">
          {failure}
        </p>
      ) : null}
    </div>
  );
}

/** Set or replace the key. It is sent once and never shown again, not even to this page. */
function KeyForm({ keySet }: { keySet: boolean }) {
  const client = useQueryClient();
  const toast = useToast();
  const [key, setKey] = useState("");
  const [problem, setProblem] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function submit(event: FormEvent) {
    event.preventDefault();
    if (busy) return;
    setBusy(true);
    setProblem(null);
    try {
      await api.setGeminiKey(key);
      setKey("");
      await client.invalidateQueries({ queryKey: keys.gemini });
      toast({ message: "Gemini key saved." });
    } catch (error) {
      setProblem(fieldProblems(error)["key"] ?? splitProblems(error, ["key"]).general);
    } finally {
      setBusy(false);
    }
  }

  const label = keySet ? "Replace key" : "Save key";
  return (
    <form className="inline-add" onSubmit={(event) => void submit(event)} noValidate>
      <Input
        label={keySet ? "New Gemini API key" : "Gemini API key"}
        type="password"
        autoComplete="off"
        spellCheck={false}
        value={key}
        onChange={(event) => setKey(event.target.value)}
        error={problem ?? undefined}
        hint="From Google AI Studio. Stored on this computer only, outside the database and backups."
      />
      {key.trim() === "" ? (
        <Button type="submit" disabled disabledReason="Paste a key first.">
          {label}
        </Button>
      ) : (
        <Button type="submit" loading={busy}>
          {label}
        </Button>
      )}
    </form>
  );
}

function ModelForm({ model }: { model: string }) {
  const client = useQueryClient();
  const toast = useToast();
  const [value, setValue] = useState(model);
  const [problem, setProblem] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const changed = value.trim() !== model;

  async function submit(event: FormEvent) {
    event.preventDefault();
    if (busy || !changed) return;
    setBusy(true);
    setProblem(null);
    try {
      await api.patchSettings({ gemini_model: value.trim() });
      await Promise.all([
        client.invalidateQueries({ queryKey: keys.gemini }),
        client.invalidateQueries({ queryKey: keys.settings }),
      ]);
      toast({ message: "Gemini model saved." });
    } catch (error) {
      setProblem(
        fieldProblems(error)["gemini_model"]
          ? "Use a model name such as gemini-3.5-flash-lite: letters, digits, dots and dashes."
          : splitProblems(error, ["gemini_model"]).general,
      );
    } finally {
      setBusy(false);
    }
  }

  return (
    <form className="inline-add" onSubmit={(event) => void submit(event)} noValidate>
      <Input
        label="Model"
        value={value}
        spellCheck={false}
        onChange={(event) => setValue(event.target.value)}
        error={problem ?? undefined}
      />
      {changed ? (
        <Button type="submit" variant="secondary" loading={busy}>
          Save model
        </Button>
      ) : (
        <Button
          type="submit"
          variant="secondary"
          disabled
          disabledReason="Type another model name."
        >
          Save model
        </Button>
      )}
    </form>
  );
}

/** A real call to Gemini with the saved key and model (API 2.9). */
function TestButton() {
  const [busy, setBusy] = useState(false);
  const [result, setResult] = useState<{ ok: boolean; text: string } | null>(null);

  async function test() {
    if (busy) return;
    setBusy(true);
    setResult(null);
    try {
      const done = await api.testGemini();
      setResult({ ok: true, text: `Connected to ${done.model} in ${done.latency_ms} ms.` });
    } catch (error) {
      setResult({ ok: false, text: splitProblems(error, []).general ?? "The test failed." });
    } finally {
      setBusy(false);
    }
  }

  return (
    <>
      <Button variant="secondary" loading={busy} onClick={() => void test()}>
        Test connection
      </Button>
      {result ? (
        <p
          role={result.ok ? "status" : "alert"}
          className={result.ok ? "section-note" : "form-failure"}
        >
          {result.text}
        </p>
      ) : null}
    </>
  );
}
