import { useId } from "react";

// A switch (DESIGN.md 6.12): a pill track with a cream thumb. "On" uses the clay colour.

interface ToggleProps {
  label: string;
  checked: boolean;
  onChange: (next: boolean) => void;
  disabled?: boolean;
  /** Shown beside a disabled switch, so a disabled control always says why. */
  disabledReason?: string;
}

export function Toggle({ label, checked, onChange, disabled, disabledReason }: ToggleProps) {
  const labelId = useId();
  const reasonId = useId();
  return (
    <div className="toggle-row">
      <span id={labelId} className="toggle-row__label">
        {label}
      </span>
      <button
        type="button"
        role="switch"
        aria-checked={checked}
        aria-labelledby={labelId}
        aria-describedby={disabled && disabledReason ? reasonId : undefined}
        disabled={disabled}
        className="toggle"
        onClick={() => onChange(!checked)}
      >
        <span className="toggle__thumb" aria-hidden="true" />
      </button>
      {disabled && disabledReason ? (
        <span id={reasonId} className="pill__reason">
          {disabledReason}
        </span>
      ) : null}
    </div>
  );
}
