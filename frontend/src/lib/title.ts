// The browser tab title (PAGES.md P-11): "Settings · Enderchest", and "(3) Settings · Enderchest"
// while three reminders are open. The page part and the count come from different places (each
// screen, the notification poll), so both are kept here and the title is written from both.

let page: string | undefined;
let open = 0;

export function titleText(pageName: string | undefined, openCount: number): string {
  const base = pageName ? `${pageName} · Enderchest` : "Enderchest";
  return openCount > 0 ? `(${openCount}) ${base}` : base;
}

function write(): void {
  document.title = titleText(page, open);
}

export function setPageName(pageName: string | undefined): void {
  page = pageName;
  write();
}

export function setOpenCount(count: number): void {
  open = count;
  write();
}
