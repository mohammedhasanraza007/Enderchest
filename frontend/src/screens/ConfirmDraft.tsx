import { useEffect, useRef, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { ApiError, idempotencyKey } from "../api/client";
import { api, fileUrl } from "../api/endpoints";
import type { Draft } from "../api/endpoints";
import { useQueryClient } from "@tanstack/react-query";
import { keys, useDraft, useRefreshInventory } from "../api/queries";
import { usePageTitle } from "../hooks/usePageTitle";
import { useUnsavedGuard } from "../hooks/useUnsavedGuard";
import { splitProblems } from "../lib/formErrors";
import { ITEM_FIELDS, toDraftFields, validate, valuesFromDraft } from "../lib/itemForm";
import type { ItemFormValues } from "../lib/itemForm";
import { ErrorState } from "../patterns/ErrorState";
import { ItemFields } from "../patterns/ItemFields";
import { Button, LinkButton } from "../primitives/Button";
import { GlassCard } from "../primitives/Glass";
import { Skeleton } from "../primitives/Skeleton";
import { useToast } from "../primitives/Toast";

// P-07, confirm one draft: its photos on the left, the item fields on the right, saved to the
// server as the owner types (so closing the browser loses nothing). Nothing is read from the photo
// in this phase; every value is the owner's own.

const SAVE_AFTER_MS = 600;

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

function ConfirmForm({ draft }: { draft: Draft }) {
  const navigate = useNavigate();
  const refresh = useRefreshInventory();
  const client = useQueryClient();
  const toast = useToast();
  const [values, setValues] = useState<ItemFormValues>(() => valuesFromDraft(draft.fields));
  const [touched, setTouched] = useState(false);
  const [saveState, setSaveState] = useState<"saved" | "pending" | "failed">("saved");
  const [serverProblems, setServerProblems] = useState<Record<string, string>>({});
  const [general, setGeneral] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [key] = useState(idempotencyKey);
  const latest = useRef(values);
  latest.current = values;
  useUnsavedGuard(saveState === "pending");

  // Saved as the owner edits: a pause in typing sends the fields (PAGES.md P-07).
  useEffect(() => {
    if (!touched) return;
    setSaveState("pending");
    const timer = window.setTimeout(() => {
      api.changeDraft(draft.id, toDraftFields(latest.current, true)).then(
        () => setSaveState("saved"),
        () => setSaveState("failed"),
      );
    }, SAVE_AFTER_MS);
    return () => window.clearTimeout(timer);
  }, [values, touched, draft.id]);

  const problems = validate(values);
  const shown: Record<string, string> = { ...serverProblems };
  if (touched) Object.assign(shown, problems);
  const firstProblem = Object.values(problems)[0];

  async function commit(next: "item" | "next") {
    if (busy) return;
    setBusy(true);
    setGeneral(null);
    try {
      await api.changeDraft(draft.id, toDraftFields(latest.current, true));
      setSaveState("saved");
      const item = await api.commitDraft(draft.id, key);
      await refresh();
      toast({ message: "Item saved." });
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
          <ItemFields
            values={values}
            onChange={(next) => {
              setTouched(true);
              setServerProblems({});
              setValues(next);
            }}
            problems={shown}
            categoryDefaults
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
          <div className="sheet-actions">
            {firstProblem ? (
              <>
                <Button type="submit" disabled disabledReason={firstProblem}>
                  Save and add next
                </Button>
                <Button variant="secondary" disabled disabledReason={firstProblem}>
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
