import type { ChatMessage, ChatReply, ChatSegment } from "../api/endpoints";

// The Assistant page's conversation (P-15). It lives in sessionStorage so following an item link
// and coming back keeps it, and is gone when the tab closes. The server keeps nothing.

export const STORAGE_KEY = "enderchest.assistant";
/** The API takes at most 20 messages (API 2.16). */
export const SENT_MAX = 20;

/** A named item's saved price, read on this laptop after Gemini answered (D-141). */
export interface SavedPrice {
  publicId: string;
  name: string;
  /** null: no price saved for this item. */
  paise: number | null;
}

export interface Turn {
  question: string;
  /** The checked answer; absent while it is on its way or after a failure. */
  reply?: {
    text: string;
    segments: ChatSegment[];
    rowsChecked: number;
    /** Only for a question about money; absent in answers saved before D-141. */
    prices?: SavedPrice[];
  };
}

function storage(): Storage | null {
  try {
    return window.sessionStorage;
  } catch {
    return null;
  }
}

function isSegment(value: unknown): boolean {
  return (
    typeof value === "object" && value !== null && typeof (value as ChatSegment).text === "string"
  );
}

function isPrice(value: unknown): boolean {
  if (typeof value !== "object" || value === null) return false;
  const price = value as SavedPrice;
  return (
    typeof price.publicId === "string" &&
    typeof price.name === "string" &&
    (price.paise === null || typeof price.paise === "number")
  );
}

// Every part the page draws is checked, so a damaged entry starts an empty chat, not a crash.
function isTurn(value: unknown): value is Turn {
  if (typeof value !== "object" || value === null) return false;
  const turn = value as Turn;
  if (typeof turn.question !== "string") return false;
  if (turn.reply === undefined) return true;
  return (
    typeof turn.reply === "object" &&
    turn.reply !== null &&
    typeof turn.reply.rowsChecked === "number" &&
    Array.isArray(turn.reply.segments) &&
    turn.reply.segments.every(isSegment) &&
    (turn.reply.prices === undefined ||
      (Array.isArray(turn.reply.prices) && turn.reply.prices.every(isPrice)))
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
  const prices = (reply.prices ?? []).map((price) => ({
    publicId: price.public_id,
    name: price.name,
    paise: price.price_paise,
  }));
  return { text: reply.reply, segments: reply.segments, rowsChecked: reply.rows_checked, prices };
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
