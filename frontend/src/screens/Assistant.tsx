import { useEffect, useRef, useState } from "react";
import type { FormEvent } from "react";
import { Link } from "react-router-dom";
import { ApiError } from "../api/client";
import { api } from "../api/endpoints";
import { useGemini, useSettings } from "../api/queries";
import { usePageTitle } from "../hooks/usePageTitle";
import { loadTurns, messagesFor, saveTurns, toReply } from "../lib/assistant";
import type { Turn } from "../lib/assistant";
import { ErrorState } from "../patterns/ErrorState";
import { Button, LinkButton } from "../primitives/Button";
import { GlassCard } from "../primitives/Glass";
import { Skeleton } from "../primitives/Skeleton";

// P-15, Assistant (Phase 9): a narrow chat about the owner's own things, as in the owner's
// reference. Gemini gets the chat and only the item rows its read-only tools return; the backend
// checks every answer, so a name the tools did not return becomes the honest miss. The
// conversation lives in this tab only (lib/assistant.ts).

const SETTINGS_LINK = "/settings#assistant-switch";

export function Assistant() {
  usePageTitle("Assistant");
  const gemini = useGemini();
  const settings = useSettings();

  let body;
  if (gemini.isPending || settings.isPending) {
    body = <Skeleton height={240} />;
  } else if (gemini.isError || settings.isError) {
    const failed = gemini.error ?? settings.error;
    body = (
      <ErrorState
        message={failed?.message ?? "The settings could not be read."}
        onRetry={() => void Promise.all([gemini.refetch(), settings.refetch()])}
      />
    );
  } else if (!gemini.data.key_set) {
    body = <Unavailable reason="no_key" />;
  } else if (!settings.data.assistant_share_item_text) {
    body = <Unavailable reason="assistant_off" />;
  } else {
    body = <Conversation />;
  }

  return (
    <div className="assistant">
      <h1 className="assistant__title">Assistant</h1>
      <p className="assistant__privacy">
        This chat and the matching item rows are sent to Gemini. Notes, photos and prices stay on
        this laptop. <Link to={SETTINGS_LINK}>Settings</Link>
      </p>
      <GlassCard className="assistant__card" aria-label="Conversation">
        {body}
      </GlassCard>
    </div>
  );
}

/** No key, or the switch is off: say which, and go straight to the switch. No input. */
function Unavailable({ reason }: { reason: "no_key" | "assistant_off" }) {
  return (
    <div className="assistant__unavailable">
      <p className="assistant__unavailable-text">
        {reason === "no_key"
          ? "The assistant needs a Gemini key. Add one in Settings, then switch on Use the assistant."
          : "The assistant is switched off. Switch on Use the assistant in Settings to ask about your things."}
      </p>
      <LinkButton to={SETTINGS_LINK}>Open Gemini settings</LinkButton>
    </div>
  );
}

function Conversation() {
  const [turns, setTurns] = useState<Turn[]>(loadTurns);
  const [draft, setDraft] = useState("");
  const [sending, setSending] = useState(false);
  const [failure, setFailure] = useState<{ message: string; disabled: boolean } | null>(null);
  const endRef = useRef<HTMLDivElement>(null);

  useEffect(() => saveTurns(turns), [turns]);
  useEffect(() => endRef.current?.scrollIntoView?.({ block: "nearest" }), [turns, sending]);

  async function ask(question: string, earlier: Turn[]) {
    setSending(true);
    setFailure(null);
    setTurns([...earlier, { question }]);
    try {
      const reply = await api.assistantChat(messagesFor(earlier, question));
      setTurns([...earlier, { question, reply: toReply(reply) }]);
      setDraft("");
    } catch (error) {
      const disabled = error instanceof ApiError && error.code === "gemini_disabled";
      setFailure({
        message: error instanceof Error ? error.message : "The question could not be sent.",
        disabled,
      });
    } finally {
      setSending(false);
    }
  }

  function submit(event: FormEvent) {
    event.preventDefault();
    const question = draft.trim();
    if (question === "" || sending) return;
    void ask(
      question,
      turns.filter((turn) => turn.reply),
    );
  }

  const last = turns.at(-1);
  const retry = last && !last.reply && !sending ? last : null;

  return (
    <div className="assistant__chat">
      {turns.length === 0 ? (
        <p className="assistant__empty">
          Ask about your things: what expires this week, where something is, how many you have.
        </p>
      ) : (
        <ol className="assistant__turns" aria-live="polite">
          {turns.map((turn, index) => (
            <li key={index} className="assistant__turn">
              <p className="assistant__question">{turn.question}</p>
              {turn.reply ? <Answer reply={turn.reply} /> : null}
            </li>
          ))}
        </ol>
      )}
      {sending ? (
        <p className="assistant__thinking" role="status">
          Checking your inventory…
        </p>
      ) : null}
      {failure && retry ? (
        failure.disabled ? (
          <p role="alert" className="form-failure">
            {failure.message} <Link to={SETTINGS_LINK}>Open Gemini settings</Link>
          </p>
        ) : (
          <ErrorState
            message={failure.message}
            onRetry={() => void ask(retry.question, turns.slice(0, -1))}
          />
        )
      ) : null}
      <div ref={endRef} />
      <form className="assistant__ask" onSubmit={submit} noValidate>
        <label className="visually-hidden" htmlFor="assistant-input">
          Your question
        </label>
        <input
          id="assistant-input"
          className="assistant__input"
          placeholder="Ask about your things…"
          maxLength={2000}
          autoComplete="off"
          value={draft}
          disabled={sending}
          onChange={(event) => setDraft(event.target.value)}
        />
        <button
          type="submit"
          className="assistant__send"
          aria-label="Send"
          disabled={sending || draft.trim() === ""}
          title={draft.trim() === "" ? "Type a question first." : undefined}
        >
          <svg viewBox="0 0 24 24" width="20" height="20" aria-hidden="true">
            <path
              d="M7 17 17 7M9 7h8v8"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
            />
          </svg>
        </button>
      </form>
      {turns.length > 0 && !sending ? (
        <Button
          variant="ghost"
          className="assistant__restart"
          onClick={() => {
            setTurns([]);
            setFailure(null);
          }}
        >
          Start over
        </Button>
      ) : null}
    </div>
  );
}

function Answer({ reply }: { reply: NonNullable<Turn["reply"]> }) {
  return (
    <div className="assistant__answer-wrap">
      <p className="assistant__answer">
        {reply.segments.map((segment, index) =>
          segment.public_id ? (
            <Link key={index} to={`/items/${segment.public_id}`}>
              {segment.text}
            </Link>
          ) : (
            <span key={index}>{segment.text}</span>
          ),
        )}
      </p>
      {reply.rowsChecked > 0 ? (
        <p className="assistant__source">
          From your inventory · {reply.rowsChecked} {reply.rowsChecked === 1 ? "item" : "items"}{" "}
          checked
        </p>
      ) : null}
    </div>
  );
}
