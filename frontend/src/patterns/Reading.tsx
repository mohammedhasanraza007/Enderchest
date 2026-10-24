import type { Draft } from "../api/endpoints";
import { FLAG_WORDS, SOURCE_LABEL } from "../lib/proposals";
import type { FieldSource } from "../lib/proposals";
import { Sheet } from "../primitives/Overlay";

// The smart-capture pieces of the confirm screen (PAGES.md P-07): where a value came from, and
// the "What was read" drawer with the raw text, the notes and Gemini's answer.

const CONFIDENCE_WORDS = {
  high: "high confidence",
  medium: "medium confidence",
  low: "low confidence, check it",
} as const;

/**
 * Read from photo, Gemini or You, with a dot for how sure the reading is: filled is high, half
 * filled is medium, an empty ring is low. The dot is a shape, never a colour alone, and the words
 * are in the accessible name.
 */
export function SourceTag({ source }: { source: FieldSource }) {
  const label = SOURCE_LABEL[source.source];
  const words = source.confidence ? CONFIDENCE_WORDS[source.confidence] : null;
  return (
    <span className="source-tag" title={words ? `${label}, ${words}` : label}>
      {source.confidence ? (
        <span
          className={`confidence-dot confidence-dot--${source.confidence}`}
          aria-hidden="true"
        />
      ) : null}
      {label}
      {words ? <span className="visually-hidden">, {words}</span> : null}
    </span>
  );
}

const GEMINI_LABELS: Array<[keyof NonNullable<Draft["gemini_values"]>, string]> = [
  ["name", "Name"],
  ["brand", "Brand"],
  ["model", "Model"],
  ["size", "Size"],
  ["category", "Category"],
  ["expiry_text", "Expiry text"],
];

/** "What was read": everything the photo reading and Gemini returned, before any choice. */
export function ReadDrawer({
  draft,
  open,
  onClose,
}: {
  draft: Draft;
  open: boolean;
  onClose: () => void;
}) {
  const info = draft.ocr_info;
  const gemini = draft.gemini_values;
  return (
    <Sheet open={open} onClose={onClose} title="What was read">
      <div className="stack read-drawer">
        <section className="stack-gap">
          <h3 className="read-drawer__heading">From the photo, on this computer</h3>
          {info ? (
            <p className="section-note">
              {info.engine}, {info.photos === 1 ? "1 photo" : `${info.photos} photos`}, in{" "}
              {(info.ms / 1000).toFixed(1)} s.
            </p>
          ) : null}
          {draft.raw_text ? (
            <pre className="read-drawer__text">{draft.raw_text}</pre>
          ) : (
            <p className="section-note">No text has been read from this photo.</p>
          )}
          {draft.read_notes.length > 0 ? (
            <ul className="read-drawer__notes">
              {draft.read_notes.map((note) => (
                <li key={note}>{note}</li>
              ))}
            </ul>
          ) : null}
        </section>
        {gemini ? (
          <section className="stack-gap">
            <h3 className="read-drawer__heading">From Gemini, unverified</h3>
            {GEMINI_LABELS.every(([key]) => !gemini[key]) && !gemini.inspection_interval_days ? (
              <p className="section-note">Gemini found nothing it could read.</p>
            ) : null}
            <dl className="read-drawer__values">
              {GEMINI_LABELS.filter(([key]) => gemini[key]).map(([key, label]) => (
                <div key={key}>
                  <dt>{label}</dt>
                  <dd>{gemini[key]}</dd>
                </div>
              ))}
              {gemini.inspection_interval_days ? (
                <div>
                  <dt>Inspection every</dt>
                  <dd>
                    {gemini.inspection_interval_days} days ({FLAG_WORDS["suggested"]}, unverified)
                  </dd>
                </div>
              ) : null}
            </dl>
          </section>
        ) : null}
      </div>
    </Sheet>
  );
}
