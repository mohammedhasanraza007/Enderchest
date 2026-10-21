// A loading placeholder shaped like the final content (PAGES.md 2). Pill-shaped; it only fades.

export function Skeleton({
  width = "100%",
  height = 20,
}: {
  width?: number | string;
  height?: number;
}) {
  return <span className="skeleton" style={{ width, height }} aria-hidden="true" />;
}
