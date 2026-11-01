import { useCallback, useEffect, useRef, useState } from "react";
import type { FormEvent } from "react";
import { Link, useNavigate } from "react-router-dom";
import { ApiError } from "../api/client";
import { api } from "../api/endpoints";
import type { CheckCandidate, CheckResult } from "../api/endpoints";
import { useRefreshInventory } from "../api/queries";
import { emptyValues } from "../lib/itemForm";
import { LEVEL_KIND, LEVEL_WORDS, checkBlocked, whyLine } from "../lib/ownership";
import { ItemFormSheet } from "../patterns/ItemFormSheet";
import { ItemPhoto } from "../patterns/ItemVisuals";
import { SavingSheet } from "../patterns/SavingSheet";
import { Button, LinkButton } from "../primitives/Button";
import { Chip } from "../primitives/Chip";
import { InnerPanel } from "../primitives/Glass";
import { Input } from "../primitives/Input";
import { StatusChip } from "../primitives/StatusChip";
import { Shutter } from "../patterns/Shutter";

// P-13, "Do I own this?": the camera hub's third mode. A desk-side check before ordering: a
// photo (shutter, upload, paste or drop) and/or typed words go to POST /ownership/check, which
// proposes up to five of the owner's items with a confidence level. The page never says
// "certain"; the owner decides, and nothing is saved without their tap (D-114, D-118).

const IMAGE_TYPES = "image/jpeg,image/png,image/webp";

export function OwnControls({
  live,
  capture,
}: {
  live: boolean;
  capture: () => Promise<Blob | null>;
}) {
  const picker = useRef<HTMLInputElement>(null);
  const [photo, setPhoto] = useState<Blob | null>(null);
  const [preview, setPreview] = useState<string | null>(null);
  const [text, setText] = useState("");
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [result, setResult] = useState<CheckResult | null>(null);

  const choose = useCallback((file: Blob | undefined) => {
    if (!file) return;
    setPhoto(file);
    setResult(null);
    setMessage(null);
  }, []);

  // The preview is an object URL for the chosen photo, released when it changes.
  useEffect(() => {
    if (!photo) {
      setPreview(null);
      return;
    }
    const url = URL.createObjectURL(photo);
    setPreview(url);
    return () => URL.revokeObjectURL(url);
  }, [photo]);

  // Ctrl+V with an image on the clipboard makes it the photo to check.
  useEffect(() => {
    function onPaste(event: ClipboardEvent) {
      const file = Array.from(event.clipboardData?.files ?? []).find((f) =>
        f.type.startsWith("image/"),
      );
      if (file) {
        event.preventDefault();
        choose(file);
      }
    }
    window.addEventListener("paste", onPaste);
    return () => window.removeEventListener("paste", onPaste);
  }, [choose]);

  const blocked = checkBlocked(photo !== null, text);

  async function submit(event: FormEvent) {
    event.preventDefault();
    if (busy || blocked) return;
    setBusy(true);
    setMessage(photo ? "Reading the photo and comparing…" : "Comparing…");
    try {
      setResult(await api.checkOwnership(photo, text));
      setMessage(null);
    } catch (error) {
      setMessage(error instanceof ApiError ? error.message : "The check did not work. Try again.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div
      className="camera-controls"
      onDragOver={(event) => event.preventDefault()}
      onDrop={(event) => {
        event.preventDefault();
        choose(Array.from(event.dataTransfer.files).find((f) => f.type.startsWith("image/")));
      }}
    >
      <p className="section-note">
        Check before you order: compare a product with what you already have, here at your desk. You
        decide; nothing is saved unless you tap.
      </p>
      {live ? (
        <Shutter
          label="Take photo to check"
          busy={busy}
          onShoot={() =>
            capture().then((blob) => {
              if (blob) choose(blob);
              else setMessage("The camera has no picture yet. Wait a moment and try again.");
            })
          }
        />
      ) : null}
      {preview ? (
        <div className="own-photo">
          <img src={preview} alt="The photo to check" className="row-list__thumb" />
          <Button variant="ghost" onClick={() => setPhoto(null)}>
            Remove photo
          </Button>
        </div>
      ) : null}
      <form className="inline-add own-form" onSubmit={(event) => void submit(event)}>
        <Input
          label="Or type what it is"
          value={text}
          placeholder="13 mm spanner"
          autoComplete="off"
          onChange={(event) => {
            setText(event.target.value);
            setResult(null);
          }}
        />
        {blocked ? (
          <Button type="submit" disabled disabledReason={blocked}>
            Check
          </Button>
        ) : (
          <Button type="submit" loading={busy}>
            Check
          </Button>
        )}
      </form>
      <div className="chip-row">
        <input
          ref={picker}
          type="file"
          accept={IMAGE_TYPES}
          hidden
          onChange={(event) => {
            const file = event.target.files?.[0];
            event.target.value = "";
            choose(file);
          }}
        />
        <Button variant="secondary" onClick={() => picker.current?.click()}>
          Upload a photo
        </Button>
      </div>
      <p className="section-note">
        Drop a photo here or paste one with Ctrl+V (a product page screenshot works too).
      </p>
      {message ? (
        <p role="status" className="camera-controls__message">
          {message}
        </p>
      ) : null}
      {result ? (
        <Results
          result={result}
          photo={photo}
          text={text}
          onDone={() => {
            setResult(null);
            setPhoto(null);
            setText("");
          }}
        />
      ) : null}
    </div>
  );
}

function Results({
  result,
  photo,
  text,
  onDone,
}: {
  result: CheckResult;
  photo: Blob | null;
  text: string;
  onDone: () => void;
}) {
  const [hidden, setHidden] = useState<Set<string>>(new Set());
  const [saving, setSaving] = useState<CheckCandidate | null>(null);
  const [recorded, setRecorded] = useState<Set<string>>(new Set());
  const shown = result.candidates.filter((candidate) => !hidden.has(candidate.public_id));

  return (
    <section className="own-results" aria-labelledby="own-results-title">
      <h2 id="own-results-title" className="own-results__title">
        {shown.length === 0
          ? "Nothing in your inventory looks like this"
          : shown.length === 1
            ? "One item may be the same"
            : `${shown.length} items may be the same`}
      </h2>
      {shown.length > 0 ? (
        <ul className="row-list">
          {shown.map((candidate) => (
            <li key={candidate.public_id} className="row-list__row">
              <ItemPhoto
                photoId={candidate.primary_photo_id}
                name={candidate.name}
                className="row-list__thumb"
              />
              <div className="row-list__text">
                <span className="row-list__line">
                  <Link to={`/items/${candidate.public_id}`}>{candidate.name}</Link>
                  <StatusChip kind={LEVEL_KIND[candidate.level]}>
                    {LEVEL_WORDS[candidate.level]}
                  </StatusChip>
                </span>
                <span className="section-note">
                  {candidate.location_path.length > 0
                    ? candidate.location_path.join(" › ")
                    : "No location"}
                  {` · quantity ${candidate.quantity}`}
                </span>
                <span className="own-why">{whyLine(candidate.reasons)}</span>
              </div>
              <div className="chip-row">
                {recorded.has(candidate.public_id) ? (
                  <Chip>Saving recorded</Chip>
                ) : (
                  <Button onClick={() => setSaving(candidate)}>I didn't buy it</Button>
                )}
                <LinkButton variant="secondary" to={`/items/${candidate.public_id}`}>
                  Open item
                </LinkButton>
                <Button
                  variant="ghost"
                  onClick={() => setHidden((now) => new Set(now).add(candidate.public_id))}
                >
                  Not the same
                </Button>
              </div>
            </li>
          ))}
        </ul>
      ) : null}
      <NoneOfThese photo={photo} text={text} onDone={onDone} />
      <SavingSheet
        item={saving}
        onClose={() => {
          setSaving(null);
        }}
        onRecorded={(publicId, isRecorded) =>
          setRecorded((now) => {
            const next = new Set(now);
            if (isRecorded) next.add(publicId);
            else next.delete(publicId);
            return next;
          })
        }
      />
    </section>
  );
}

// Always present under the results: the owner may decide none of them is the same thing.
function NoneOfThese({
  photo,
  text,
  onDone,
}: {
  photo: Blob | null;
  text: string;
  onDone: () => void;
}) {
  const navigate = useNavigate();
  const refresh = useRefreshInventory();
  const [open, setOpen] = useState(false);
  const [busy, setBusy] = useState(false);
  const [manual, setManual] = useState(false);
  const [message, setMessage] = useState<string | null>(null);

  async function addIt() {
    if (!photo) {
      setManual(true); // words only: the new-item form, named from the words (D-118)
      return;
    }
    setBusy(true);
    try {
      const { drafts } = await api.createDrafts([photo]);
      await refresh();
      const first = drafts[0];
      navigate(first ? `/add/${first.id}` : "/add");
    } catch (error) {
      setMessage(error instanceof ApiError ? error.message : "The photo could not be saved.");
      setBusy(false);
    }
  }

  return (
    <InnerPanel className="own-none">
      {open ? (
        <>
          <p className="own-none__text">Then you probably do not have it yet.</p>
          <div className="chip-row">
            <Button variant="secondary" loading={busy} onClick={() => void addIt()}>
              Add it to my inventory
            </Button>
            <Button variant="ghost" onClick={onDone}>
              I'll buy it
            </Button>
          </div>
          {message ? (
            <p role="alert" className="field__error">
              {message}
            </p>
          ) : null}
        </>
      ) : (
        <Button variant="secondary" onClick={() => setOpen(true)}>
          None of these
        </Button>
      )}
      <ItemFormSheet
        open={manual}
        initial={{ ...emptyValues(), name: text.trim().slice(0, 120) }}
        onClose={() => setManual(false)}
        onSaved={() => undefined}
      />
    </InnerPanel>
  );
}
