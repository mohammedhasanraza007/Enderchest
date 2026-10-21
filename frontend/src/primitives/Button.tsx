import { useId } from "react";
import type { ButtonHTMLAttributes, ReactNode } from "react";
import { Link } from "react-router-dom";
import type { LinkProps } from "react-router-dom";

// The pill button (DESIGN.md 6.10). Three looks: primary (cream), secondary (glass), ghost.
// A disabled button must say why, so `disabledReason` is required whenever `disabled` is true.

export type ButtonVariant = "primary" | "secondary" | "ghost";

interface Common {
  variant?: ButtonVariant;
  /** While a request runs: the label stays, a small dot appears, and clicks are ignored. */
  loading?: boolean;
  children: ReactNode;
}
type Enabled = { disabled?: false; disabledReason?: undefined };
type Disabled = { disabled: true; disabledReason: string };

export type ButtonProps = Common &
  (Enabled | Disabled) &
  Omit<ButtonHTMLAttributes<HTMLButtonElement>, "disabled" | "children">;

function classNames(variant: ButtonVariant, loading: boolean, extra?: string): string {
  return ["pill", `pill--${variant}`, loading ? "is-loading" : "", extra ?? ""]
    .filter(Boolean)
    .join(" ");
}

export function Button({
  variant = "primary",
  loading = false,
  disabled,
  disabledReason,
  children,
  className,
  onClick,
  type = "button",
  ...rest
}: ButtonProps) {
  const reasonId = useId();
  return (
    <>
      <button
        {...rest}
        type={type}
        className={classNames(variant, loading, className)}
        disabled={disabled}
        aria-busy={loading || undefined}
        aria-describedby={disabled ? reasonId : rest["aria-describedby"]}
        onClick={(event) => {
          if (loading) {
            event.preventDefault(); // a second click while the first is running does nothing
            return;
          }
          onClick?.(event);
        }}
      >
        {children}
        {loading ? <span className="pill__dot" aria-hidden="true" /> : null}
      </button>
      {disabled ? (
        <span id={reasonId} className="pill__reason">
          {disabledReason}
        </span>
      ) : null}
    </>
  );
}

/** A link that looks like a button, for actions that go to another page. */
export function LinkButton({
  variant = "primary",
  className,
  ...rest
}: LinkProps & { variant?: ButtonVariant }) {
  return <Link {...rest} className={classNames(variant, false, className)} />;
}
