import { beforeEach, describe, expect, it, vi } from "vitest";
import { loadTurns, messagesFor, saveTurns, SENT_MAX, STORAGE_KEY } from "./assistant";
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
});
