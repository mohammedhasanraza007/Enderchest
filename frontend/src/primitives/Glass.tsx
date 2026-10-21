import type { HTMLAttributes, ReactNode } from "react";

// Frosted surfaces (DESIGN.md 4.3). The fills are opaque tokens; the blur is only cosmetic.
// A card may hold one inner panel, which has no blur of its own.

interface GlassCardProps extends Omit<HTMLAttributes<HTMLElement>, "title"> {
  /** A serif title shown at the top of the card. */
  title?: string;
  /** The heading level of the title, so a page keeps a sensible outline. */
  headingLevel?: 1 | 2 | 3;
  children: ReactNode;
}

export function GlassCard({
  title,
  headingLevel = 2,
  children,
  className,
  ...rest
}: GlassCardProps) {
  const Heading = `h${headingLevel}` as const;
  return (
    <section {...rest} className={["glass-card", className ?? ""].filter(Boolean).join(" ")}>
      {title ? <Heading className="glass-card__title">{title}</Heading> : null}
      {children}
    </section>
  );
}

export function InnerPanel({ children, className, ...rest }: HTMLAttributes<HTMLDivElement>) {
  return (
    <div {...rest} className={["inner-panel", className ?? ""].filter(Boolean).join(" ")}>
      {children}
    </div>
  );
}
