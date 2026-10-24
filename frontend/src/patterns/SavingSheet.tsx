import { useState } from "react";
import type { FormEvent } from "react";
import { api } from "../api/endpoints";
import { idempotencyKey } from "../api/client";
import { useRefreshInventory } from "../api/queries";
import { formatRupees, paiseToInput } from "../lib/money";
import { savingPrice } from "../lib/ownership";
import { Button } from "../primitives/Button";
import { Input, TextArea } from "../primitives/Input";
import { Sheet } from "../primitives/Overlay";
import { useToast } from "../primitives/Toast";

// "I didn't buy it" (P-13): the owner types the price they did not spend; nothing is counted
// until they press Save (CLAUDE.md 6, no estimates). The toast offers Undo for 60 seconds.

export function SavingSheet({
  item,
  onClose,
}: {
  item: { public_id: string; name: string; price_paise: number | null } | null;
  onClose: () => void;
}) {
  return item ? <OpenSavingSheet item={item} onClose={onClose} /> : null;
}

function OpenSavingSheet({
  item,
  onClose,
}: {
  item: { public_id: string; name: string; price_paise: number | null };
  onClose: () => void;
}) {
  const [price, setPrice] = useState(paiseToInput(item.price_paise));
  const [note, setNote] = useState("");
  const [touched, setTouched] = useState(false);
  const [saving, setSaving] = useState(false);
  const [general, setGeneral] = useState<string | null>(null);
  const [key] = useState(idempotencyKey);
  const refresh = useRefreshInventory();
  const toast = useToast();
  const parsed = savingPrice(price);
  const problem = "problem" in parsed ? parsed.problem : null;

  async function save(event: FormEvent) {
    event.preventDefault();
    setTouched(true);
    if (saving || "problem" in parsed) return;
    setSaving(true);
    try {
      const done = await api.addSaving(
        { item_public_id: item.public_id, price_paise: parsed.paise, note: note.trim() },
        key,
      );
      await refresh();
      onClose();
      toast({
        message: `${formatRupees(parsed.paise)} saved on ${item.name}.`,
        actionLabel: "Undo",
        onAction: () => void api.undo(done.event_id).then(refresh),
      });
    } catch (error) {
      setGeneral(error instanceof Error ? error.message : "The saving could not be recorded.");
      setSaving(false);
    }
  }

  return (
    <Sheet open onClose={onClose} title="I didn't buy it">
      <form className="stack" onSubmit={(event) => void save(event)} noValidate>
        <p className="section-note">
          Record what you did not spend on {item.name}. Only the price you type counts.
        </p>
        <Input
          label="Price saved (₹)"
          value={price}
          inputMode="decimal"
          autoComplete="off"
          required
          error={touched ? (problem ?? undefined) : undefined}
          onChange={(event) => setPrice(event.target.value)}
          onBlur={() => setTouched(true)}
        />
        <TextArea
          label="Note (optional)"
          value={note}
          rows={2}
          onChange={(event) => setNote(event.target.value)}
        />
        {general ? (
          <p role="alert" className="field__error">
            {general}
          </p>
        ) : null}
        <div className="chip-row">
          {problem ? (
            <Button type="submit" disabled disabledReason={problem}>
              Save
            </Button>
          ) : (
            <Button type="submit" loading={saving}>
              Save
            </Button>
          )}
          <Button variant="ghost" onClick={onClose}>
            Cancel
          </Button>
        </div>
      </form>
    </Sheet>
  );
}
