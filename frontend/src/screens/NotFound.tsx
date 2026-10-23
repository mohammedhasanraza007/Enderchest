import { usePageTitle } from "../hooks/usePageTitle";
import { LinkButton } from "../primitives/Button";
import { BrandMark } from "../primitives/BrandMark";
import { GlassCard } from "../primitives/Glass";

// P-17: a calm card with the logo mark and a way home (PAGES.md). The item page uses the same
// card with its own title for an unknown id (P-04).

export function NotFound({ title = "That page doesn't exist" }: { title?: string }) {
  usePageTitle("Not found");
  return (
    <div className="center-card">
      <BrandMark size={72} />
      <GlassCard title={title} headingLevel={1}>
        <p className="stack-gap">The address may be mistyped, or the page may have moved.</p>
        <LinkButton to="/">Go home</LinkButton>
      </GlassCard>
    </div>
  );
}
