import type { ChatMessage, ChatReply, ChatSegment } from "../api/endpoints";

// The Assistant page's conversation (P-15). It lives in sessionStorage so following an item link
// and coming back keeps it, and is gone when the tab closes. The server keeps nothing.

export const STORAGE_KEY = "enderchest.assistant";
/** The API takes at most 20 messages (API 2.16). */
export const SENT_MAX = 20;

export interface Turn {
  question: string;
  /** The checked answer; absent while it is on its way or after a failure. */
  reply?: { text: string; segments: ChatSegment[]; rowsChecked: number };
}

function storage(): Storage | null {
  try {
    return window.sessionStorage;
  } catch {
    return null;
  }
}

function isTurn(value: unknown): value is Turn {
  if (typeof value !== "object" || value === null) return false;
  const turn = value as Turn;
  return (
    typeof turn.question === "string" &&
    (turn.reply === undefined || Array.isArray(turn.reply.segments))
  );
}

/** The saved conversation, or an empty one when there is none or it cannot be read. */
export function loadTurns(): Turn[] {
  try {
    const parsed: unknown = JSON.parse(storage()?.getItem(STORAGE_KEY) ?? "[]");
    return Array.isArray(parsed) && parsed.every(isTurn) ? parsed : [];
  } catch {
    return [];
  }
}

export function saveTurns(turns: Turn[]): void {
  try {
    const store = storage();
    if (turns.length === 0) store?.removeItem(STORAGE_KEY);
    else store?.setItem(STORAGE_KEY, JSON.stringify(turns));
  } catch {
    // A full or blocked store only means the chat is not kept across pages.
  }
}

export function toReply(reply: ChatReply): NonNullable<Turn["reply"]> {
  return { text: reply.reply, segments: reply.segments, rowsChecked: reply.rows_checked };
}

/**
 * The messages for the next request: answered turns as question and answer pairs, then the new
 * question; only the newest 20, starting with a question as the API requires. Unanswered earlier
 * turns (a failure the owner moved past) are left out.
 */
export function messagesFor(turns: Turn[], question: string): ChatMessage[] {
  const messages: ChatMessage[] = [];
  for (const turn of turns) {
    if (!turn.reply) continue;
    messages.push({ role: "user", content: turn.question });
    messages.push({ role: "assistant", content: turn.reply.text });
  }
  messages.push({ role: "user", content: question });
  const recent = messages.slice(-SENT_MAX);
  return recent[0]?.role === "user" ? recent : recent.slice(1);
}
