// The supplied logo, exactly as supplied (DESIGN.md 4.9): an image, never recoloured, tinted,
// outlined, glowed, rotated or animated, and never placed inside a pill or glass fill.

interface BrandMarkProps {
  size: 32 | 72 | 96;
  /** True beside the wordmark, where the picture adds nothing for a screen reader. */
  decorative?: boolean;
}

export function BrandMark({ size, decorative = false }: BrandMarkProps) {
  return (
    <img
      className="brand-mark"
      src="/enderchest-logo.svg"
      width={size}
      height={size}
      alt={decorative ? "" : "Enderchest"}
    />
  );
}
