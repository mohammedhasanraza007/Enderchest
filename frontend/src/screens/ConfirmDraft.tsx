import { useEffect, useId, useRef, useState } from "react";
import { announceDelivery } from "../lib/motion";
import { useNavigate, useParams } from "react-router-dom";
import { ApiError, idempotencyKey } from "../api/client";
import { api, fileUrl } from "../api/endpoints";
import type { Draft, Proposal } from "../api/endpoints";
import { useQueryClient } from "@tanstack/react-query";
import { keys, useDraft, useGemini, useRefreshInventory } from "../api/queries";
import { usePageTitle } from "../hooks/usePageTitle";
import { useUnsavedGuard } from "../hooks/useUnsavedGuard";
import { formatDay } from "../lib/format";
import { splitProblems } from "../lib/formErrors";
import { ITEM_FIELDS, toDraftFields, validate, valuesFromDraft } from "../lib/itemForm";
import type { ItemFormValues } from "../lib/itemForm";
import {
  FLAG_WORDS,
  PROPOSAL_FIELDS,
  applyProposals,
  changedFields,
  formValue,
  ownedFields,
  sourcesFor,
} from "../lib/proposals";
import type { ProposalField, Proposed } from "../lib/proposals";
import { ErrorState } from "../patterns/ErrorState";
import { ItemFields } from "../patterns/ItemFields";
import { ReadDrawer } from "../patterns/Reading";
import { Button, LinkButton } from "../primitives/Button";
import { Chip } from "../primitives/Chip";
import { GlassCard } from "../primitives/Glass";
import { Skeleton } from "../primitives/Skeleton";
import { StatusChip } from "../primitives/StatusChip";
import { useToast } from "../primitives/Toast";

// P-07, confirm one draft: its photos on the left, the item fields on the right, saved to the
// server as the owner types (so closing the browser loses nothing). Values read from the photo
// (or suggested by Gemini) fill only the fields the owner has not made their own, each with a
// tag saying where it came from; a read expiry date counts only once the owner taps it (D-100).

const SAVE_AFTER_MS = 600;
const CONFIRM_REASON = "Confirm the expiry date.";

export function ConfirmDraft() {
  const { draftId = "" } = useParams();
  const draft = useDraft(draftId);
  usePageTitle("Review");

  if (draft.isPending) {
    return (
      <div className="confirm" aria-busy="true">
        <Skeleton height={360} />
        <Skeleton height={480} />
      </div>
    );
  }
  if (draft.isError) {
    return (
      <GlassCard>
        <ErrorState message={draft.error.message} onRetry={() => void draft.refetch()} />
      </GlassCard>
    );
  }
  if (draft.data.status !== "open") {
    return (
      <GlassCard title="This photo is done" headingLevel={1}>
        <p className="stack-gap">
          It was already {draft.data.status === "committed" ? "saved as an item" : "discarded"}.
        </p>
        <LinkButton to="/add">Back to the review list</LinkButton>
      </GlassCard>
    );
  }
  return <ConfirmForm key={draft.data.id} draft={draft.data} />;
}

/** True when the date in the form is the read one (or its other reading), not one typed in. */
function readExpiry(values: ItemFormValues, proposal: Proposal | undefined): boolean {
  if (!proposal || values.expiry_mode !== "date") return false;
  return [String(proposal.value), ...(proposal.alternatives ?? [])].includes(values.expiry_date);
}

function ConfirmForm({ draft }: { draft: Draft }) {
  const navigate = useNavigate();
  const refresh = useRefreshInventory();
  const client = useQueryClient();
  const toast = useToast();
  const proposed: Proposed = draft.proposed;
  // The fields the owner has made their own; proposals never touch them (D-100).
  const owned = useRef<Set<ProposalField>>(
    ownedFields(valuesFromDraft(draft.fields), proposed, draft.fields.owned ?? []),
  );
  const [values, setValues] = useState<ItemFormValues>(() =>
    applyProposals(valuesFromDraft(draft.fields), proposed, owned.current),
  );
  const [expiryConfirmed, setExpiryConfirmed] = useState<boolean>(
    () =>
      draft.fields.expiry_confirmed ??
      !readExpiry(
        applyProposals(valuesFromDraft(draft.fields), proposed, owned.current),
        proposed["expiry_date"],
      ),
  );
  const [touched, setTouched] = useState(false);
  const [dirty, setDirty] = useState(false);
  const [saveState, setSaveState] = useState<"saved" | "pending" | "failed">("saved");
  const [serverProblems, setServerProblems] = useState<Record<string, string>>({});
  const [general, setGeneral] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [key] = useState(idempotencyKey);
  const reasonId = useId();
  const latest = useRef(values);
  latest.current = values;
  const confirmedNow = useRef(expiryConfirmed);
  confirmedNow.current = expiryConfirmed;
  useUnsavedGuard(saveState === "pending");

  // A reading that finishes while the page is open fills the fields still left to it.
  const proposedKey = JSON.stringify(proposed);
  const applied = useRef(proposedKey);
  useEffect(() => {
    if (applied.current === proposedKey) return;
    applied.current = proposedKey;
    const before = latest.current;
    const next = applyProposals(before, proposed, owned.current);
    if (formValue(next, "expiry_date") !== formValue(before, "expiry_date")) {
      setExpiryConfirmed(!readExpiry(next, proposed["expiry_date"]));
    }
    setValues(next);
    setDirty(true);
  }, [proposedKey, proposed]);

  // Saved as the owner edits: a pause in typing sends the fields (PAGES.md P-07).
  useEffect(() => {
    if (!dirty) return;
    setSaveState("pending");
    const timer = window.setTimeout(() => {
      api
        .changeDraft(draft.id, toDraftFields(latest.current, confirmedNow.current, owned.current))
        .then(
          () => setSaveState("saved"),
          () => setSaveState("failed"),
        );
    }, SAVE_AFTER_MS);
    return () => window.clearTimeout(timer);
  }, [values, expiryConfirmed, dirty, draft.id]);

  const problems = validate(values);
  const shown: Record<string, string> = { ...serverProblems };
  if (touched) Object.assign(shown, problems);
  const needsConfirm =
    values.expiry_mode === "date" && values.expiry_date !== "" && !expiryConfirmed;
  const firstProblem = Object.values(problems)[0] ?? (needsConfirm ? CONFIRM_REASON : undefined);
  const expiryProposal = proposed["expiry_date"];

  function edit(next: ItemFormValues) {
    const before = latest.current;
    for (const field of changedFields(before, next)) owned.current.add(field);
    // A date the owner types or changes is their own, so it needs no extra tap.
    if (formValue(next, "expiry_date") !== formValue(before, "expiry_date")) {
      setExpiryConfirmed(true);
    }
    setTouched(true);
    setServerProblems({});
    setValues(next);
    setDirty(true);
  }

  function confirmDate(day: string) {
    owned.current.add("expiry_date");
    setValues({ ...latest.current, expiry_mode: "date", expiry_date: day });
    setExpiryConfirmed(true);
    setDirty(true);
  }

  async function commit(next: "item" | "next") {
    if (busy) return;
    setBusy(true);
    setGeneral(null);
    try {
      await api.changeDraft(
        draft.id,
        toDraftFields(latest.current, confirmedNow.current, owned.current),
      );
      setSaveState("saved");
      const item = await api.commitDraft(draft.id, key);
      await refresh();
      toast({ message: "Item saved." });
      announceDelivery();
      if (next === "item") {
        navigate(`/items/${item.public_id}`);
        return;
      }
      const open = await client.fetchQuery({ queryKey: keys.drafts, queryFn: api.drafts });
      const waiting = open.items.filter((d) => d.id !== draft.id);
      const following = waiting[0];
      navigate(following ? `/add/${following.id}` : "/camera?mode=add");
    } catch (error) {
      const found = splitProblems(error, ITEM_FIELDS);
      setServerProblems(found.fields);
      setGeneral(
        found.general ??
          (error instanceof ApiError && error.code === "expiry_unconfirmed" ? error.message : null),
      );
    } finally {
      setBusy(false);
    }
  }

  async function discard() {
    if (busy) return;
    setBusy(true);
    try {
      await api.discardDraft(draft.id);
      await refresh();
      navigate("/add");
    } catch (error) {
      setGeneral(error instanceof Error ? error.message : "Something went wrong.");
      setBusy(false);
    }
  }

  return (
    <div className="confirm">
      <DraftPhotos draft={draft} />
      <GlassCard title="Confirm the item" headingLevel={1}>
        <form
          className="stack"
          noValidate
          onSubmit={(event) => {
            event.preventDefault();
            if (!firstProblem) void commit("next");
          }}
        >
          <ReadingPanel draft={draft} />
          <ItemFields
            values={values}
            onChange={edit}
            problems={shown}
            categoryDefaults
            sources={sourcesFor(values, proposed)}
            expiryNote={
              readExpiry(values, expiryProposal) && expiryProposal ? (
                <ExpiryCheck
                  proposal={expiryProposal}
                  chosen={values.expiry_date}
                  confirmed={expiryConfirmed}
                  onConfirm={confirmDate}
                />
              ) : null
            }
          />
          <p className="section-note" role="status">
            {saveState === "pending"
              ? "Saving your changes…"
              : saveState === "failed"
                ? "Your last change was not saved. Keep typing to try again."
                : "Changes are saved as you type."}
          </p>
          {general ? (
            <p role="alert" className="form-failure">
              {general}
            </p>
          ) : null}
          {firstProblem ? (
            <p id={reasonId} className="pill__reason">
              To save: {firstProblem}
            </p>
          ) : null}
          <div className="sheet-actions">
            {firstProblem ? (
              <>
                <Button type="submit" disabled disabledReasonId={reasonId}>
                  Save and add next
                </Button>
                <Button variant="secondary" disabled disabledReasonId={reasonId}>
                  Save item
                </Button>
              </>
            ) : (
              <>
                <Button type="submit" loading={busy}>
                  Save and add next
                </Button>
                <Button variant="secondary" loading={busy} onClick={() => void commit("item")}>
                  Save item
                </Button>
              </>
            )}
            <Button variant="ghost" onClick={() => void discard()}>
              Discard draft
            </Button>
          </div>
        </form>
      </GlassCard>
    </div>
  );
}

/** A read expiry date: "Not confirmed" until tapped; an ambiguous one offers both readings. */
function ExpiryCheck({
  proposal,
  chosen,
  confirmed,
  onConfirm,
}: {
  proposal: Proposal;
  chosen: string;
  confirmed: boolean;
  onConfirm: (day: string) => void;
}) {
  const pickId = useId();
  const readings = [String(proposal.value), ...(proposal.alternatives ?? [])];
  const reasons = proposal.flags.filter((flag) => FLAG_WORDS[flag]).map((flag) => FLAG_WORDS[flag]);
  return (
    <div className="expiry-check">
      <div className="expiry-check__status">
        {confirmed ? (
          <StatusChip kind="success">Confirmed</StatusChip>
        ) : (
          <StatusChip kind="warning">Not confirmed</StatusChip>
        )}
        {proposal.text ? <span className="section-note">Read “{proposal.text}”</span> : null}
      </div>
      {reasons.length > 0 ? <p className="section-note">Check it: {reasons.join("; ")}.</p> : null}
      {readings.length > 1 ? (
        <>
          <p className="section-note" id={pickId}>
            Which date is printed?
          </p>
          <div className="chip-row" role="radiogroup" aria-labelledby={pickId}>
            {readings.map((day) => (
              <Chip
                key={day}
                role="radio"
                selected={confirmed && chosen === day}
                onSelect={() => onConfirm(day)}
              >
                {formatDay(day)}
              </Chip>
            ))}
          </div>
        </>
      ) : confirmed ? null : (
        <Button variant="secondary" onClick={() => onConfirm(chosen)}>
          Confirm {formatDay(chosen)}
        </Button>
      )}
    </div>
  );
}

/** Reading state, Re-read, Improve with Gemini and the "What was read" drawer. */
function ReadingPanel({ draft }: { draft: Draft }) {
  const client = useQueryClient();
  const gemini = useGemini();
  const [drawer, setDrawer] = useState(false);
  const [failure, setFailure] = useState<string | null>(null);
  const [asking, setAsking] = useState<"local" | "gemini" | null>(null);
  const reading = draft.ocr_status === "pending";
  const askingGemini = draft.gemini_status === "pending";
  const geminiOn = gemini.data !== undefined && gemini.data.key_set && gemini.data.mode !== "off";
  const filled = PROPOSAL_FIELDS.filter((field) => draft.proposed[field]).length;
  const fromGemini = Object.values(draft.proposed).filter((p) => p.source === "gemini").length;

  async function extract(engine: "local" | "gemini") {
    if (asking) return;
    setAsking(engine);
    setFailure(null);
    try {
      await api.extract(draft.id, engine);
      await client.invalidateQueries({ queryKey: keys.draft(draft.id) });
    } catch (error) {
      setFailure(splitProblems(error, []).general);
    } finally {
      setAsking(null);
    }
  }

  const status =
    draft.ocr_status === "pending"
      ? "Reading the photo…"
      : draft.ocr_status === "none"
        ? "This photo has not been read yet."
        : draft.ocr_status === "failed"
          ? null
          : filled === 0
            ? "Nothing useful was read from the photo. Fill in the fields yourself."
            : `Filled ${filled === 1 ? "1 field" : `${filled} fields`} from the photo. Check each one before saving.`;
  const geminiStatus =
    draft.gemini_status === "pending"
      ? "Asking Gemini…"
      : draft.gemini_status === "done"
        ? fromGemini === 0
          ? "Gemini added nothing the photo reading did not already have."
          : `Gemini filled ${fromGemini === 1 ? "1 field" : `${fromGemini} fields`} (unverified).`
        : draft.gemini_status === "skipped"
          ? "Gemini was not asked: the photo gave a name or a model."
          : null;

  return (
    <div className="reading-panel">
      {status ? (
        <p className="section-note" role="status">
          {status}
        </p>
      ) : null}
      {draft.ocr_status === "failed" && draft.ocr_error ? (
        <p role="alert" className="form-failure">
          {draft.ocr_error}
        </p>
      ) : null}
      {geminiStatus ? <p className="section-note">{geminiStatus}</p> : null}
      {draft.gemini_status === "failed" && draft.gemini_error ? (
        <p role="alert" className="form-failure">
          {draft.gemini_error}
        </p>
      ) : null}
      {failure ? (
        <p role="alert" className="form-failure">
          {failure}
        </p>
      ) : null}
      <div className="reading-panel__actions">
        {reading ? (
          <Button variant="secondary" disabled disabledReason="The photo is being read.">
            Re-read
          </Button>
        ) : (
          <Button
            variant="secondary"
            loading={asking === "local"}
            onClick={() => void extract("local")}
          >
            {draft.ocr_status === "none" ? "Read the photo" : "Re-read"}
          </Button>
        )}
        {geminiOn ? (
          reading || askingGemini ? (
            <Button
              variant="secondary"
              disabled
              disabledReason={
                reading ? "Wait for the photo reading to finish." : "Gemini is answering."
              }
            >
              Improve with Gemini
            </Button>
          ) : (
            <Button
              variant="secondary"
              loading={asking === "gemini"}
              onClick={() => void extract("gemini")}
            >
              Improve with Gemini
            </Button>
          )
        ) : null}
        {draft.raw_text !== null || draft.gemini_values ? (
          <Button variant="ghost" onClick={() => setDrawer(true)}>
            What was read
          </Button>
        ) : null}
      </div>
      {geminiOn && gemini.data ? (
        <p className="section-note">
          Improve with Gemini sends the text read from this photo
          {gemini.data.share_images ? ", and the photo itself," : ""} to Google Gemini. Its answers
          are suggestions and are not checked.
        </p>
      ) : null}
      <ReadDrawer draft={draft} open={drawer} onClose={() => setDrawer(false)} />
    </div>
  );
}

function DraftPhotos({ draft }: { draft: Draft }) {
  const refresh = useRefreshInventory();
  const picker = useRef<HTMLInputElement>(null);
  const [busy, setBusy] = useState(false);
  const [failure, setFailure] = useState<string | null>(null);
  const [first, ...rest] = draft.photos;
  return (
    <div className="confirm__photos">
      {first ? (
        <img
          className="photo-frame__image confirm__main"
          src={fileUrl.photo(first.id)}
          alt="The photo for this item"
        />
      ) : null}
      {rest.length > 0 ? (
        <div className="photo-strip">
          {rest.map((photo) => (
            <img
              key={photo.id}
              className="photo-strip__thumb"
              src={fileUrl.thumb(photo.id)}
              alt=""
            />
          ))}
        </div>
      ) : null}
      <input
        ref={picker}
        type="file"
        accept="image/jpeg,image/png,image/webp"
        hidden
        onChange={(event) => {
          const file = event.target.files?.[0];
          event.target.value = "";
          if (!file || busy) return;
          setBusy(true);
          setFailure(null);
          api
            .addDraftPhoto(draft.id, file)
            .then(refresh)
            .catch((error: unknown) => setFailure(splitProblems(error, []).general))
            .finally(() => setBusy(false));
        }}
      />
      {draft.photos.length < 12 ? (
        <Button variant="secondary" loading={busy} onClick={() => picker.current?.click()}>
          Add photo
        </Button>
      ) : (
        <Button variant="secondary" disabled disabledReason="12 photos is the most.">
          Add photo
        </Button>
      )}
      {failure ? (
        <p role="alert" className="form-failure">
          {failure}
        </p>
      ) : null}
    </div>
  );
}
