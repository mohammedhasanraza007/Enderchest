import { usePageTitle } from "../hooks/usePageTitle";
import { LinkButton } from "../primitives/Button";
import { BrandMark } from "../primitives/BrandMark";
import { GlassCard } from "../primitives/Glass";

// P-17: a calm card with the logo mark and a way home (PAGES.md).

export function NotFound() {
  usePageTitle("Not found");
  return (
    <div className="center-card">
      <BrandMark size={72} />
      <GlassCard title="That page doesn't exist" headingLevel={1}>
        <p className="stack-gap">The address may be mistyped, or the page may have moved.</p>
        <LinkButton to="/">Go home</LinkButton>
      </GlassCard>
    </div>
  );
}
