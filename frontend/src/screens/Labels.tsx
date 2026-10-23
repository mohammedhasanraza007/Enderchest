import { useState } from "react";
import { useSearchParams } from "react-router-dom";
import { api, fileUrl } from "../api/endpoints";
import type { ItemDetail } from "../api/endpoints";
import { useItemsById, useRefreshInventory } from "../api/queries";
import { usePageTitle } from "../hooks/usePageTitle";
import { Button, LinkButton } from "../primitives/Button";
import { Chip } from "../primitives/Chip";
import { GlassCard, InnerPanel } from "../primitives/Glass";
import { Skeleton } from "../primitives/Skeleton";
import { useToast } from "../primitives/Toast";

// P-08, the label sheet. Two layouts at their real sizes: an A4 sheet of 3 × 7 labels
// (63.5 × 38.1 mm) or single 50 × 30 mm labels. Print uses the browser's print dialog with a print
// stylesheet; the browser cannot tell whether paper came out, so "printed" is set only when the
// owner says yes afterwards (D-045).

type Layout = "a4" | "single";
const PER_SHEET = 21;

export function Labels() {
  usePageTitle("Labels");
  const [params] = useSearchParams();
  const ids = [...new Set((params.get("ids") ?? "").split(",").map((id) => id.trim()))]
    .filter(Boolean)
    .slice(0, 200);
  const results = useItemsById(ids);
  const refresh = useRefreshInventory();
  const toast = useToast();
  const [layout, setLayout] = useState<Layout>("a4");
  const [asking, setAsking] = useState(false);
  const [busy, setBusy] = useState(false);
  const [failure, setFailure] = useState<string | null>(null);

  const loading = results.some((result) => result.isPending);
  const loaded = results.flatMap((result) => (result.data ? [result.data] : []));
  const missing = ids.filter((_, index) => results[index]?.isError);
  const printable = loaded.filter((item) => !item.label.no_label_needed && !item.deleted_at);
  const skipped = loaded.filter((item) => item.label.no_label_needed);

  async function markPrinted() {
    if (busy) return;
    setBusy(true);
    setFailure(null);
    try {
      const { updated } = await api.labelPrinted(printable.map((item) => item.public_id));
      await refresh();
      toast({
        message:
          updated === 1 ? "1 label marked as printed." : `${updated} labels marked as printed.`,
      });
      setAsking(false);
    } catch (error) {
      setFailure(error instanceof Error ? error.message : "Something went wrong.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="labels">
      <div className="labels-controls">
        <div className="page-head">
          <h1 className="page-title">Labels</h1>
          <div className="page-head__actions">
            {printable.length > 0 ? (
              <Button
                onClick={() => {
                  window.print();
                  setAsking(true);
                }}
              >
                Print
              </Button>
            ) : (
              <Button
                disabled
                disabledReason={loading ? "Loading the labels…" : "There is nothing to print."}
              >
                Print
              </Button>
            )}
          </div>
        </div>
        <div className="chip-row" role="radiogroup" aria-label="Label layout">
          <Chip role="radio" selected={layout === "a4"} onSelect={() => setLayout("a4")}>
            A4 sheet, 3 × 7 (63.5 × 38.1 mm)
          </Chip>
          <Chip role="radio" selected={layout === "single"} onSelect={() => setLayout("single")}>
            Single label (50 × 30 mm)
          </Chip>
        </div>
        {asking ? (
          <InnerPanel className="print-question" role="status">
            <p>Did the labels print?</p>
            <Button loading={busy} onClick={() => void markPrinted()}>
              Yes, mark as printed
            </Button>
            <Button variant="secondary" onClick={() => setAsking(false)}>
              No
            </Button>
          </InnerPanel>
        ) : null}
        {failure ? (
          <p role="alert" className="form-failure">
            {failure}
          </p>
        ) : null}
        {ids.length === 0 ? (
          <GlassCard className="empty-state">
            <p>No items were chosen for labels.</p>
            <LinkButton to="/inventory">Choose items in Inventory</LinkButton>
          </GlassCard>
        ) : null}
        {skipped.length > 0 || missing.length > 0 ? (
          <GlassCard title="Skipped" headingLevel={2}>
            <ul className="row-list">
              {skipped.map((item) => (
                <li key={item.public_id} className="row-list__row">
                  {item.name}: marked "I don't need a printed label".
                </li>
              ))}
              {missing.map((id) => (
                <li key={id} className="row-list__row">
                  {id}: no item with that ID.
                </li>
              ))}
            </ul>
          </GlassCard>
        ) : null}
      </div>

      {loading ? (
        <Skeleton height={400} />
      ) : printable.length > 0 ? (
        <div className="label-preview">
          {layout === "a4" ? <A4Sheets items={printable} /> : <SingleLabels items={printable} />}
        </div>
      ) : null}

      {printable.length > 0 ? (
        <GlassCard title="Download a QR code" headingLevel={2} className="labels-controls">
          <ul className="row-list">
            {printable.map((item) => (
              <li key={item.public_id} className="row-list__row">
                <span className="row-list__text">{item.name}</span>
                <a
                  className="pill pill--secondary"
                  href={fileUrl.qr(item.public_id)}
                  download={`${item.public_id}.svg`}
                >
                  Download QR
                </a>
              </li>
            ))}
          </ul>
        </GlassCard>
      ) : null}
    </div>
  );
}

function Label({ item }: { item: ItemDetail }) {
  return (
    <div className="print-label">
      <img className="print-label__qr" src={fileUrl.qr(item.public_id)} alt="" />
      <div className="print-label__text">
        <span className="print-label__id">{item.public_id}</span>
        <span className="print-label__name">{item.name}</span>
      </div>
    </div>
  );
}

function A4Sheets({ items }: { items: ItemDetail[] }) {
  const sheets: ItemDetail[][] = [];
  for (let start = 0; start < items.length; start += PER_SHEET) {
    sheets.push(items.slice(start, start + PER_SHEET));
  }
  return (
    <>
      {sheets.map((sheet, index) => (
        <div key={index} className="print-sheet print-sheet--a4" aria-label={`Sheet ${index + 1}`}>
          {sheet.map((item) => (
            <Label key={item.public_id} item={item} />
          ))}
        </div>
      ))}
    </>
  );
}

function SingleLabels({ items }: { items: ItemDetail[] }) {
  return (
    <>
      {items.map((item) => (
        <div key={item.public_id} className="print-sheet print-sheet--single">
          <Label item={item} />
        </div>
      ))}
    </>
  );
}
