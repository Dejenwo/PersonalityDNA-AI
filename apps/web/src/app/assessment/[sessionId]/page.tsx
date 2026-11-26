"use client";

import { ApiError, type AssessmentDetail, type SessionOut } from "@pdna/api-client";
import { useParams, useRouter } from "next/navigation";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { LikertQuestion } from "@/components/likert";
import { Button, ButtonLink, Card, ErrorState, LoadingState, ProgressBar } from "@/components/ui";
import { api } from "@/lib/api";
import { AnswerQueue, type QueueStatus } from "@/lib/answer-queue";
import { errorMessage, isNotFound } from "@/lib/errors";
import { rememberResult, tokenForSession } from "@/lib/token";

type Load =
  | { status: "loading" }
  | { status: "error"; error: unknown; noToken?: boolean }
  | { status: "ready"; session: SessionOut; assessment: AssessmentDetail; token: string };

const statusText: Record<QueueStatus, string> = {
  idle: "",
  saving: "Saving…",
  saved: "All answers saved",
  retrying: "Connection problem. We'll keep trying to save your answers.",
  error: "Your answers could not be saved.",
};

export default function AssessmentPage() {
  const { sessionId } = useParams<{ sessionId: string }>();
  const router = useRouter();
  const [load, setLoad] = useState<Load>({ status: "loading" });
  const [answers, setAnswers] = useState<Record<string, number>>({});
  const [index, setIndex] = useState(0);
  const [reviewing, setReviewing] = useState(false);
  const [saveStatus, setSaveStatus] = useState<QueueStatus>("idle");
  const [finishing, setFinishing] = useState(false);
  const [finishError, setFinishError] = useState<string | null>(null);
  const queueRef = useRef<AnswerQueue | null>(null);
  const advanceRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const headingRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    let alive = true;
    (async () => {
      const token = tokenForSession(sessionId);
      if (!token) {
        setLoad({ status: "error", error: null, noToken: true });
        return;
      }
      try {
        const session = await api.getSession(sessionId, token);
        if (session.status === "completed" && session.result_id) {
          rememberResult(sessionId, session.result_id);
          router.replace(`/results/${session.result_id}`);
          return;
        }
        const assessment = await api.getAssessment(session.instrument_id);
        if (!alive) return;
        setAnswers(session.answers);
        const firstOpen = assessment.items.findIndex((i) => session.answers[i.id] === undefined);
        if (firstOpen === -1) setReviewing(true);
        setIndex(firstOpen === -1 ? assessment.items.length - 1 : firstOpen);
        queueRef.current = new AnswerQueue(
          async (batch) => {
            await api.saveAnswers(sessionId, token, batch);
          },
          {
            onStatus: (s) => alive && setSaveStatus(s),
            isFatal: (e) => e instanceof ApiError && e.status >= 400 && e.status < 500 && e.status !== 429,
          },
        );
        setLoad({ status: "ready", session, assessment, token });
      } catch (error) {
        if (alive) setLoad({ status: "error", error });
      }
    })();
    return () => {
      alive = false;
    };
  }, [sessionId, router]);

  // Warn before leaving with unsaved answers.
  useEffect(() => {
    const handler = (e: BeforeUnloadEvent) => {
      if (queueRef.current?.hasPending) e.preventDefault();
    };
    window.addEventListener("beforeunload", handler);
    return () => window.removeEventListener("beforeunload", handler);
  }, []);

  useEffect(() => () => {
    if (advanceRef.current) clearTimeout(advanceRef.current);
  }, []);

  const items = useMemo(() => (load.status === "ready" ? load.assessment.items : []), [load]);
  const answered = items.filter((i) => answers[i.id] !== undefined).length;
  const unanswered = items.filter((i) => answers[i.id] === undefined);

  const go = useCallback(
    (next: number) => {
      if (advanceRef.current) clearTimeout(advanceRef.current);
      if (next >= items.length) {
        setReviewing(true);
      } else {
        setReviewing(false);
        setIndex(Math.max(0, next));
      }
      requestAnimationFrame(() => headingRef.current?.focus());
    },
    [items.length],
  );

  const choose = (itemId: string, value: number) => {
    const updated = { ...answers, [itemId]: value };
    setAnswers(updated);
    queueRef.current?.put(itemId, value);
    // Advance to the next unanswered statement after this one; if there is none, go to review.
    const nextOpen = items.findIndex((it, i) => i > index && updated[it.id] === undefined);
    if (advanceRef.current) clearTimeout(advanceRef.current);
    advanceRef.current = setTimeout(() => go(nextOpen === -1 ? items.length : nextOpen), 250);
  };

  async function finish() {
    if (load.status !== "ready") return;
    setFinishing(true);
    setFinishError(null);
    try {
      await queueRef.current?.flush();
      const result = await api.completeSession(sessionId, load.token);
      rememberResult(sessionId, result.id);
      router.push(`/results/${result.id}#t=${encodeURIComponent(load.token)}`);
    } catch (err) {
      setFinishError(errorMessage(err));
      setFinishing(false);
    }
  }

  if (load.status === "loading") return <LoadingState label="Loading your assessment" />;
  if (load.status === "error") {
    const missing = load.noToken || isNotFound(load.error);
    return (
      <ErrorState
        title={missing ? "We can't find this assessment on this device" : "We couldn't load your assessment"}
        message={
          missing
            ? "Assessments are saved on the device where you started them. Start a new one, or open this link on the original device."
            : errorMessage(load.error)
        }
        action={<ButtonLink href="/discover">Start a new assessment</ButtonLink>}
      />
    );
  }

  const item = items[index]!;
  const pct = (answered / items.length) * 100;

  return (
    <div className="mx-auto max-w-2xl">
      <div className="flex items-center justify-between gap-4 text-sm text-ink-muted">
        <span>
          {answered} of {items.length} answered
        </span>
        <span aria-live="polite" className={saveStatus === "error" || saveStatus === "retrying" ? "text-danger" : ""}>
          {statusText[saveStatus]}
        </span>
      </div>
      <div className="mt-2">
        <ProgressBar value={pct} label="Assessment progress" />
      </div>

      <div ref={headingRef} tabIndex={-1} className="mt-10 outline-none">
        {reviewing ? (
          <Card>
            <h1 className="text-2xl font-semibold">
              {unanswered.length === 0 ? "All done. Ready to see your results?" : "Almost there"}
            </h1>
            {unanswered.length > 0 ? (
              <>
                <p className="mt-2 text-ink-muted">
                  You have {unanswered.length} unanswered statement{unanswered.length === 1 ? "" : "s"}. Answering all
                  of them gives the most reliable result.
                </p>
                <ul className="mt-4 flex flex-wrap gap-2">
                  {unanswered.map((u) => (
                    <li key={u.id}>
                      <Button variant="secondary" onClick={() => go(u.number - 1)}>
                        Statement {u.number}
                      </Button>
                    </li>
                  ))}
                </ul>
              </>
            ) : (
              <p className="mt-2 text-ink-muted">
                Your answers are saved. You can go back and change any of them before finishing.
              </p>
            )}
            {finishError && (
              <p role="alert" className="mt-4 text-danger">
                {finishError}
              </p>
            )}
            <div className="mt-6 flex flex-wrap gap-3">
              <Button onClick={finish} disabled={finishing}>
                {finishing ? "Calculating…" : "See my results"}
              </Button>
              <Button variant="secondary" onClick={() => go(items.length - 1)}>
                Back to statements
              </Button>
            </div>
          </Card>
        ) : (
          <LikertQuestion
            key={item.id}
            itemId={item.id}
            number={item.number}
            text={item.text}
            options={load.assessment.response_options}
            value={answers[item.id]}
            onChange={(v) => choose(item.id, v)}
          />
        )}
      </div>

      {!reviewing && (
        <nav aria-label="Statement navigation" className="mt-8 flex items-center justify-between gap-3">
          <Button variant="secondary" onClick={() => go(index - 1)} disabled={index === 0}>
            Back
          </Button>
          <span className="text-sm text-ink-muted">
            Statement {index + 1} of {items.length}
          </span>
          <Button variant={answers[item.id] === undefined ? "ghost" : "primary"} onClick={() => go(index + 1)}>
            {answers[item.id] === undefined ? "Skip" : index === items.length - 1 ? "Review" : "Next"}
          </Button>
        </nav>
      )}
    </div>
  );
}
