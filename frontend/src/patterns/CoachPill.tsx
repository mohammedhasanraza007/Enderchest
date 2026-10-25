import type { CoachChip } from "../hooks/useCoach";

// The camera coach's words and detection chips over the live view (DESIGN.md 9). One message at
// a time in a frosted pill near the bottom, the nav's material made opaque so the words stay
// readable over any picture (D-059). The pill is a polite live region that stays in place while
// quiet, so a screen reader hears each new message once. Chips mark where the model number and
// the date were read; they repeat the message, so screen readers skip them.

const CHIP_WORDS: Record<CoachChip["kind"], string> = { model: "Model number", date: "Date" };

export function CoachPill({ message, chips }: { message: string | null; chips: CoachChip[] }) {
  return (
    <div className="coach">
      {chips.map((chip) => (
        <span
          key={chip.kind}
          className={`coach-chip${chip.below ? " coach-chip--below" : ""}`}
          style={{ left: `${chip.left}%`, top: `${chip.top}%` }}
          aria-hidden="true"
        >
          {CHIP_WORDS[chip.kind]}
        </span>
      ))}
      <p className={`coach-pill${message ? "" : " coach-pill--quiet"}`} role="status">
        {message ?? ""}
      </p>
    </div>
  );
}
