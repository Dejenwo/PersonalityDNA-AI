"use client";

import { ApiError, type CoachMessage, type Conversation } from "@pdna/api-client";
import { useParams, useRouter } from "next/navigation";
import { useEffect, useRef, useState, type FormEvent, type KeyboardEvent } from "react";
import { CoachText } from "@/components/coach-text";
import { FormMessage } from "@/components/form";
import { Button, ButtonLink, Card, ErrorState, LoadingState } from "@/components/ui";
import { api } from "@/lib/api";
import { limitMessage } from "@/lib/coach";
import { errorMessage, isNotFound } from "@/lib/errors";
import { useRequireSignIn } from "@/lib/require-auth";
import { useAsync } from "@/lib/use-async";

const MAX_CHARS = 4000;

export default function ConversationPage() {
  const { conversationId } = useParams<{ conversationId: string }>();
  const auth = useRequireSignIn();
  const signedIn = auth.status === "signed-in";
  const conv = useAsync(
    () => (signedIn ? api.getConversation(conversationId) : Promise.resolve(null)),
    `${conversationId}:${signedIn}`,
  );

  if (!signedIn || conv.status === "loading" || (conv.status === "success" && !conv.data))
    return <LoadingState label="Loading the conversation" />;
  if (conv.status === "error")
    return (
      <ErrorState
        title={isNotFound(conv.error) ? "Conversation not found" : "We couldn't load this conversation"}
        message={isNotFound(conv.error) ? "It may have been deleted." : errorMessage(conv.error)}
        action={<ButtonLink href="/coach">All conversations</ButtonLink>}
      />
    );
  return <Chat conversation={conv.data!} />;
}

function Chat({ conversation }: { conversation: Conversation }) {
  const router = useRouter();
  const [added, setAdded] = useState<CoachMessage[]>([]);
  const [draft, setDraft] = useState("");
  const [streaming, setStreaming] = useState<{ user: string; text: string } | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [remaining, setRemaining] = useState<number | null>(null);
  const [announcement, setAnnouncement] = useState("");
  const [confirmDelete, setConfirmDelete] = useState(false);
  const [deleteError, setDeleteError] = useState<string | null>(null);
  const endRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);
  const messages = [...conversation.messages, ...added];

  useEffect(() => {
    endRef.current?.scrollIntoView({ block: "end" });
  }, [messages.length, streaming?.text]);

  async function send(e?: FormEvent) {
    e?.preventDefault();
    const content = draft.trim();
    if (!content || streaming) return;
    setDraft("");
    setError(null);
    setAnnouncement("");
    setStreaming({ user: content, text: "" });
    let ended = false;
    const restore = (message: string) => {
      setError(message);
      setDraft(content);
    };
    try {
      await api.streamCoachMessage(conversation.id, content, (ev) => {
        if (ev.event === "delta") setStreaming((s) => s && { ...s, text: s.text + ev.data.text });
        else if (ev.event === "retract") setStreaming((s) => s && { ...s, text: "" });
        else if (ev.event === "done") {
          ended = true;
          setAdded((m) => [...m, ev.data.user_message, ev.data.assistant_message]);
          setRemaining(ev.data.remaining);
          setAnnouncement("The coach replied.");
        } else if (ev.event === "error") {
          ended = true;
          restore(ev.data.message);
        }
      });
      if (!ended) restore("The connection dropped before the coach finished. Please try again.");
    } catch (err) {
      restore(err instanceof ApiError && err.code === "coach_limit_reached" ? limitMessage(err.details) : errorMessage(err));
    } finally {
      setStreaming(null);
      inputRef.current?.focus();
    }
  }

  function onKeyDown(e: KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === "Enter" && !e.shiftKey && !e.nativeEvent.isComposing) {
      e.preventDefault();
      void send();
    }
  }

  async function remove() {
    setDeleteError(null);
    try {
      await api.deleteConversation(conversation.id);
      router.push("/coach");
    } catch (err) {
      setDeleteError(errorMessage(err));
    }
  }

  return (
    <div className="mx-auto max-w-3xl">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <ButtonLink href="/coach" variant="ghost" className="-ms-5">
            ← All conversations
          </ButtonLink>
          <h1 className="text-2xl font-bold">{conversation.title}</h1>
          <p className="text-sm text-ink-muted">
            {conversation.uses_results ? "The coach can see your shared assessment results." : "No results shared in this conversation."}
          </p>
        </div>
        {!confirmDelete ? (
          <Button variant="secondary" onClick={() => setConfirmDelete(true)}>
            Delete conversation
          </Button>
        ) : (
          <div role="group" aria-label="Confirm deletion" className="flex flex-wrap items-center gap-2">
            <span className="text-sm">Delete permanently?</span>
            <Button onClick={remove}>Delete</Button>
            <Button variant="secondary" onClick={() => setConfirmDelete(false)}>
              Cancel
            </Button>
          </div>
        )}
      </div>
      {deleteError && <FormMessage kind="error">{deleteError}</FormMessage>}

      <ol aria-label="Conversation" className="mt-8 space-y-4">
        {messages.length === 0 && !streaming && (
          <li className="text-ink-muted">
            Ask anything about your results or an everyday situation. For example: &ldquo;How can I use my strengths at
            work?&rdquo;
          </li>
        )}
        {messages.map((m) => (
          <MessageBubble key={m.id} role={m.role} kind={m.kind} text={m.content} />
        ))}
        {streaming && (
          <>
            <MessageBubble role="user" kind="message" text={streaming.user} />
            <li aria-busy="true">
              <Card as="div" className="bg-surface">
                <span className="sr-only">Coach is replying: </span>
                {streaming.text ? (
                  <CoachText text={streaming.text} />
                ) : (
                  <span className="text-ink-muted">The coach is thinking…</span>
                )}
              </Card>
            </li>
          </>
        )}
      </ol>
      <div ref={endRef} />
      <div aria-live="polite" className="sr-only">
        {announcement}
      </div>

      <form onSubmit={send} className="mt-6 space-y-2">
        <label htmlFor="coach-message" className="font-medium">
          Message the coach
        </label>
        <textarea
          id="coach-message"
          ref={inputRef}
          value={draft}
          onChange={(e) => setDraft(e.target.value)}
          onKeyDown={onKeyDown}
          maxLength={MAX_CHARS}
          rows={3}
          className="block w-full rounded-card border border-line bg-surface p-3 text-ink"
          aria-describedby="coach-help"
        />
        {error && <FormMessage kind="error">{error}</FormMessage>}
        <div className="flex flex-wrap items-center justify-between gap-3">
          <p id="coach-help" className="text-sm text-ink-muted">
            Enter to send, Shift+Enter for a new line.
            {draft.length > MAX_CHARS - 500 && ` ${MAX_CHARS - draft.length} characters left.`}
            {remaining !== null && ` ${remaining} messages left today.`}
          </p>
          <Button type="submit" disabled={!!streaming || !draft.trim()}>
            {streaming ? "Replying…" : "Send"}
          </Button>
        </div>
        <p className="text-xs text-ink-muted">
          The coach is an AI and can be wrong. It isn&apos;t a therapist and can&apos;t diagnose. If you are in danger,
          contact local emergency services.
        </p>
      </form>
    </div>
  );
}

function MessageBubble({ role, kind, text }: { role: string; kind: string; text: string }) {
  if (role === "user") {
    return (
      <li className="flex justify-end">
        <div className="max-w-[85%] whitespace-pre-wrap rounded-card bg-primary px-4 py-3 text-on-primary">
          <span className="sr-only">You said: </span>
          {text}
        </div>
      </li>
    );
  }
  if (kind === "crisis_support") {
    return (
      <li>
        <Card as="div" role="note" aria-label="Support is available" className="border-2 border-accent">
          <h2 className="mb-2 font-semibold">Support is available</h2>
          <CoachText text={text} />
        </Card>
      </li>
    );
  }
  return (
    <li>
      <Card as="div">
        <span className="sr-only">Coach said: </span>
        <CoachText text={text} />
      </Card>
    </li>
  );
}
