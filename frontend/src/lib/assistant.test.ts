import { beforeEach, describe, expect, it, vi } from "vitest";
import { loadTurns, messagesFor, saveTurns, SENT_MAX, STORAGE_KEY, toReply } from "./assistant";
import type { Turn } from "./assistant";

const answered = (n: number): Turn => ({
  question: `q${n}`,
  reply: { text: `a${n}`, segments: [{ text: `a${n}`, public_id: null }], rowsChecked: 0 },
});

// The unit tests run in node: a small in-memory store stands in for the tab's sessionStorage.
beforeEach(() => {
  const data = new Map<string, string>();
  vi.stubGlobal("window", {
    sessionStorage: {
      getItem: (key: string) => data.get(key) ?? null,
      setItem: (key: string, value: string) => void data.set(key, value),
      removeItem: (key: string) => void data.delete(key),
    },
  });
});

describe("messagesFor", () => {
  it("sends answered turns as pairs, then the new question", () => {
    expect(messagesFor([answered(1)], "next")).toEqual([
      { role: "user", content: "q1" },
      { role: "assistant", content: "a1" },
      { role: "user", content: "next" },
    ]);
  });

  it("leaves out a turn that never got an answer", () => {
    expect(messagesFor([{ question: "failed" }], "again")).toEqual([
      { role: "user", content: "again" },
    ]);
  });

  it("keeps at most 20 messages and always starts with a question", () => {
    const turns = Array.from({ length: 15 }, (_, i) => answered(i));
    const sent = messagesFor(turns, "last");
    expect(sent.length).toBeLessThanOrEqual(SENT_MAX);
    expect(sent[0]?.role).toBe("user");
    expect(sent.at(-1)).toEqual({ role: "user", content: "last" });
  });
});

describe("saved conversation", () => {
  it("round-trips and clears", () => {
    saveTurns([answered(1)]);
    expect(loadTurns()).toEqual([answered(1)]);
    saveTurns([]);
    expect(window.sessionStorage.getItem(STORAGE_KEY)).toBeNull();
  });

  it("ignores broken or foreign data", () => {
    window.sessionStorage.setItem(STORAGE_KEY, "{not json");
    expect(loadTurns()).toEqual([]);
    window.sessionStorage.setItem(STORAGE_KEY, JSON.stringify([{ nope: 1 }]));
    expect(loadTurns()).toEqual([]);
  });

  it("ignores a damaged answer instead of drawing it (Phase 9 verification)", () => {
    for (const reply of [
      null,
      { segments: [null], rowsChecked: 0 },
      { segments: [{}], rowsChecked: 0 },
      { segments: [] },
    ]) {
      window.sessionStorage.setItem(STORAGE_KEY, JSON.stringify([{ question: "x", reply }]));
      expect(loadTurns()).toEqual([]);
    }
  });
});

describe("saved prices (D-141)", () => {
  const reply = {
    reply: "Supernova.",
    segments: [{ text: "Supernova", public_id: "ENDR-AB0Y5YZN" }],
    cited: [{ public_id: "ENDR-AB0Y5YZN", name: "Supernova" }],
    prices: [{ public_id: "ENDR-AB0Y5YZN", name: "Supernova", price_paise: 179900 }],
    tools_used: ["search_items"],
    rows_checked: 1,
  };

  it("keeps the prices the server read on this laptop", () => {
    expect(toReply(reply).prices).toEqual([
      { publicId: "ENDR-AB0Y5YZN", name: "Supernova", paise: 179900 },
    ]);
  });

  it("still loads an answer saved before prices existed, and drops a damaged price", () => {
    saveTurns([answered(1)]);
    expect(loadTurns()).toEqual([answered(1)]);
    const damaged = { ...toReply(reply), prices: [{ publicId: "x", name: "y", paise: "1799" }] };
    window.sessionStorage.setItem(STORAGE_KEY, JSON.stringify([{ question: "x", reply: damaged }]));
    expect(loadTurns()).toEqual([]);
  });
});
