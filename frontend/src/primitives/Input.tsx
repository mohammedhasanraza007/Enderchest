import { useId } from "react";
import type {
  InputHTMLAttributes,
  ReactNode,
  SelectHTMLAttributes,
  TextareaHTMLAttributes,
} from "react";
import { ChevronDown, CircleAlert } from "lucide-react";

// Text input and select (DESIGN.md 6.12): a pill with the label above in muted text.
// An error shows a border, an icon and the message beneath, never colour alone.

interface FieldProps {
  label: string;
  hint?: string;
  error?: string;
  /** Beside the label, for example where a read value came from (P-07). */
  aside?: ReactNode;
}

function FieldLabel({ id, label, aside }: { id: string; label: string; aside?: ReactNode }) {
  const text = (
    <label className="field__label" htmlFor={id}>
      {label}
    </label>
  );
  return aside ? (
    <div className="field__label-row">
      {text}
      {aside}
    </div>
  ) : (
    text
  );
}

function FieldMessage({ id, error, hint }: { id: string; error?: string; hint?: string }) {
  if (error) {
    return (
      <p id={id} className="field__error">
        <span className="field__error-icon" aria-hidden="true">
          <CircleAlert size={16} strokeWidth={1.5} />
        </span>
        {error}
      </p>
    );
  }
  return hint ? (
    <p id={id} className="field__hint">
      {hint}
    </p>
  ) : null;
}

export function Input({
  label,
  hint,
  error,
  aside,
  className,
  ...rest
}: FieldProps & Omit<InputHTMLAttributes<HTMLInputElement>, "className"> & { className?: string }) {
  const id = useId();
  const messageId = `${id}-message`;
  return (
    <div className={["field", className ?? ""].filter(Boolean).join(" ")}>
      <FieldLabel id={id} label={label} aside={aside} />
      <input
        {...rest}
        id={id}
        className="field__control"
        aria-invalid={error ? true : undefined}
        aria-describedby={error || hint ? messageId : undefined}
      />
      <FieldMessage id={messageId} error={error} hint={hint} />
    </div>
  );
}

/** A multi-line field (notes), same label and message rules as Input. */
export function TextArea({
  label,
  hint,
  error,
  aside,
  className,
  ...rest
}: FieldProps &
  Omit<TextareaHTMLAttributes<HTMLTextAreaElement>, "className"> & { className?: string }) {
  const id = useId();
  const messageId = `${id}-message`;
  return (
    <div className={["field", className ?? ""].filter(Boolean).join(" ")}>
      <FieldLabel id={id} label={label} aside={aside} />
      <textarea
        {...rest}
        id={id}
        className="field__control field__control--area"
        aria-invalid={error ? true : undefined}
        aria-describedby={error || hint ? messageId : undefined}
      />
      <FieldMessage id={messageId} error={error} hint={hint} />
    </div>
  );
}

export interface SelectOption {
  value: string;
  label: string;
}

export function Select({
  label,
  hint,
  error,
  aside,
  options,
  className,
  ...rest
}: FieldProps & { options: SelectOption[]; className?: string } & Omit<
    SelectHTMLAttributes<HTMLSelectElement>,
    "className" | "children"
  >) {
  const id = useId();
  const messageId = `${id}-message`;
  return (
    <div className={["field", className ?? ""].filter(Boolean).join(" ")}>
      <FieldLabel id={id} label={label} aside={aside} />
      <div className="field__select">
        <select
          {...rest}
          id={id}
          className="field__control"
          aria-invalid={error ? true : undefined}
          aria-describedby={error || hint ? messageId : undefined}
        >
          {options.map((option) => (
            <option key={option.value} value={option.value}>
              {option.label}
            </option>
          ))}
        </select>
        <ChevronDown className="field__chevron" size={18} strokeWidth={1.5} aria-hidden="true" />
      </div>
      <FieldMessage id={messageId} error={error} hint={hint} />
    </div>
  );
}
