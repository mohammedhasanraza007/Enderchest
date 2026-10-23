// Markup checks for the primitives, rendered on the server with react-dom/server (no DOM needed).
// How they look in both themes is the browser gallery's job (tests/e2e/primitives.spec.ts); this
// checks what a screen reader and a keyboard get.

import type { ReactElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { StaticRouter } from "react-router-dom";
import { describe, expect, it } from "vitest";
import { BrandMark } from "./BrandMark";
import { Button, LinkButton } from "./Button";
import { Chip } from "./Chip";
import { GlassCard, InnerPanel } from "./Glass";
import { Input, Select, TextArea } from "./Input";
import { LiveBadge } from "./LiveBadge";
import { Skeleton } from "./Skeleton";
import { StatusChip } from "./StatusChip";
import { Toggle } from "./Toggle";

const html = (node: ReactElement) => renderToStaticMarkup(node);

describe("Button", () => {
  it("is a real button that does not submit by accident", () => {
    expect(html(<Button>Save</Button>)).toContain('type="button"');
  });
  it("shows a visible reason next to a disabled button and links it", () => {
    const markup = html(
      <Button disabled disabledReason="Nothing to save yet.">
        Save
      </Button>,
    );
    expect(markup).toContain("disabled");
    expect(markup).toContain("Nothing to save yet.");
    expect(markup).toMatch(/aria-describedby="([^"]+)"[\s\S]*id="\1"/);
  });
  it("keeps its label and adds a progress dot while loading", () => {
    const markup = html(<Button loading>Back up now</Button>);
    expect(markup).toContain("Back up now");
    expect(markup).toContain('aria-busy="true"');
    expect(markup).toContain("pill__dot");
  });
  it("has three looks", () => {
    for (const variant of ["primary", "secondary", "ghost"] as const) {
      expect(html(<Button variant={variant}>x</Button>)).toContain(`pill--${variant}`);
    }
  });
  it("can be a link that looks like a button", () => {
    const markup = html(
      <StaticRouter location="/">
        <LinkButton to="/settings">Open settings</LinkButton>
      </StaticRouter>,
    );
    expect(markup).toContain('href="/settings"');
    expect(markup).toContain("pill--primary");
  });
});

describe("TextArea", () => {
  it("ties the label to the field and links its error", () => {
    const markup = html(<TextArea label="Notes" error="Too long." />);
    expect(markup).toMatch(/<label[^>]*for="([^"]+)"[\s\S]*<textarea[^>]*id="\1"/);
    expect(markup).toContain('aria-invalid="true"');
    expect(markup).toContain("Too long.");
  });
});

describe("Input and Select", () => {
  it("ties the label to the field", () => {
    const markup = html(<Input label="Your name" />);
    expect(markup).toMatch(
      /<label[^>]*for="([^"]+)"[^>]*>Your name<\/label>[\s\S]*<input[^>]*id="\1"/,
    );
  });
  it("marks an error as invalid, shows the message and an icon", () => {
    const markup = html(<Input label="Your name" error="Enter a name." />);
    expect(markup).toContain('aria-invalid="true"');
    expect(markup).toContain("Enter a name.");
    expect(markup).toContain("<svg");
    expect(markup).toContain("aria-describedby");
  });
  it("renders a select with its options", () => {
    const markup = html(
      <Select label="Time zone" options={[{ value: "UTC", label: "UTC" }]} defaultValue="UTC" />,
    );
    expect(markup).toContain("<select");
    expect(markup).toMatch(/<option[^>]*value="UTC"[^>]*>UTC<\/option>/);
  });
});

describe("Toggle and Chip", () => {
  it("is a switch with its state and a name", () => {
    const markup = html(<Toggle label="A switch" checked onChange={() => undefined} />);
    expect(markup).toContain('role="switch"');
    expect(markup).toContain('aria-checked="true"');
    expect(markup).toContain("A switch");
  });
  it("is a radio when it belongs to a choice, a plain label otherwise", () => {
    const radio = html(
      <Chip role="radio" selected onSelect={() => undefined}>
        Dark
      </Chip>,
    );
    expect(radio).toContain('role="radio"');
    expect(radio).toContain('aria-checked="true"');
    expect(radio).toContain("<svg"); // the chosen chip has a check mark, not only a tint
    const other = html(
      <Chip role="radio" selected={false} onSelect={() => undefined}>
        Light
      </Chip>,
    );
    expect(other).toContain('aria-checked="false"');
    expect(other).not.toContain("<svg");
    expect(html(<Chip>Label</Chip>)).toBe('<span class="chip">Label</span>');
  });
});

describe("StatusChip", () => {
  it("is never colour alone: an icon and a word", () => {
    for (const kind of ["success", "warning", "danger", "info"] as const) {
      const markup = html(<StatusChip kind={kind}>Word</StatusChip>);
      expect(markup).toContain(`status-chip--${kind}`);
      expect(markup).toContain("<svg");
      expect(markup).toContain("Word");
    }
  });
});

describe("GlassCard, InnerPanel, Skeleton, BrandMark, LiveBadge", () => {
  it("gives a card its title at the chosen heading level", () => {
    expect(html(<GlassCard title="Profile">x</GlassCard>)).toContain("<h2");
    expect(
      html(
        <GlassCard title="Welcome" headingLevel={1}>
          x
        </GlassCard>,
      ),
    ).toContain("<h1");
    expect(html(<GlassCard>x</GlassCard>)).not.toContain("<h2");
  });
  it("nests an inner panel", () => {
    expect(html(<InnerPanel>x</InnerPanel>)).toContain("inner-panel");
  });
  it("hides a skeleton from assistive technology", () => {
    expect(html(<Skeleton />)).toContain('aria-hidden="true"');
  });
  it("shows the supplied logo file untouched, named only when it stands alone", () => {
    const alone = html(<BrandMark size={72} />);
    expect(alone).toContain('src="/enderchest-logo.svg"');
    expect(alone).toContain('alt="Enderchest"');
    expect(html(<BrandMark size={32} decorative />)).toContain('alt=""');
    expect(alone).not.toContain("style=");
  });
  it("says LIVE", () => {
    expect(html(<LiveBadge />)).toContain("LIVE");
  });
});
