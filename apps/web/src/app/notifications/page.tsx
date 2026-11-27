"use client";

import type { AppNotification, NotificationPreference } from "@pdna/api-client";
import Link from "next/link";
import { useState } from "react";
import { FormMessage } from "@/components/form";
import { Button, Card, EmptyState, ErrorState, LoadingState } from "@/components/ui";
import { useI18n } from "@/i18n/provider";
import { api } from "@/lib/api";
import { errorMessage } from "@/lib/errors";
import { useRequireSignIn } from "@/lib/require-auth";
import { useAsync } from "@/lib/use-async";

export default function NotificationsPage() {
  const auth = useRequireSignIn();
  const userId = auth.status === "signed-in" ? auth.user.id : "";
  const data = useAsync(
    () => (userId ? Promise.all([api.notifications(), api.notificationPreferences()]) : Promise.resolve(null)),
    userId,
  );

  if (auth.status !== "signed-in" || data.status === "loading" || (data.status === "success" && !data.data))
    return <LoadingState label="Loading your notifications" />;
  if (data.status === "error")
    return (
      <ErrorState level={1}
        title="We couldn't load your notifications"
        message={errorMessage(data.error)}
        action={<Button onClick={data.reload}>Try again</Button>}
      />
    );
  const [page, prefs] = data.data!;
  return (
    <div className="mx-auto max-w-3xl space-y-10">
      <header>
        <h1 className="text-3xl font-bold">Notifications</h1>
        <p className="mt-2 text-ink-muted">
          Reminders and updates about your account. They never quote your answers, journal, goals or coaching. Old
          notifications are removed after 90 days.
        </p>
      </header>
      <Inbox initial={page.notifications} initialUnread={page.unread} initialNext={page.next_before ?? null} />
      <Preferences initial={prefs} />
    </div>
  );
}

function Inbox({
  initial,
  initialUnread,
  initialNext,
}: {
  initial: AppNotification[];
  initialUnread: number;
  initialNext: string | null;
}) {
  const { formatDate } = useI18n();
  const [items, setItems] = useState(initial);
  const [unread, setUnread] = useState(initialUnread);
  const [next, setNext] = useState(initialNext);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function run(task: () => Promise<void>) {
    setBusy(true);
    setError(null);
    try {
      await task();
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setBusy(false);
    }
  }

  const markRead = (id: string) =>
    run(async () => {
      await api.readNotification(id);
      setItems((all) => all.map((n) => (n.id === id ? { ...n, read: true } : n)));
      setUnread((n) => Math.max(0, n - 1));
    });
  const markAll = () =>
    run(async () => {
      await api.readAllNotifications();
      setItems((all) => all.map((n) => ({ ...n, read: true })));
      setUnread(0);
    });
  const older = () =>
    run(async () => {
      if (!next) return;
      const page = await api.notifications(next);
      setItems((all) => [...all, ...page.notifications]);
      setNext(page.next_before ?? null);
    });

  return (
    <section aria-labelledby="inbox-heading">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h2 id="inbox-heading" className="text-xl font-semibold">
          {unread > 0 ? `Inbox (${unread} unread)` : "Inbox"}
        </h2>
        {unread > 0 && (
          <Button variant="secondary" onClick={markAll} disabled={busy}>
            Mark all as read
          </Button>
        )}
      </div>
      {error && <FormMessage kind="error">{error}</FormMessage>}
      {items.length === 0 ? (
        <EmptyState
          title="Nothing here yet"
          message="You'll see reminders and updates here, such as when someone accepts your invitation to compare."
        />
      ) : (
        <ul className="mt-4 space-y-3">
          {items.map((n) => (
            <li
              key={n.id}
              className={`rounded-card border p-4 ${n.read ? "border-line bg-surface" : "border-primary bg-muted"}`}
            >
              <div className="flex flex-wrap items-start justify-between gap-2">
                <div>
                  <p className="font-semibold">
                    {!n.read && <span className="sr-only">Unread: </span>}
                    {n.title}
                  </p>
                  {n.body && <p className="mt-1 text-sm text-ink-muted">{n.body}</p>}
                  <p className="mt-1 text-xs text-ink-muted">
                    <time dateTime={n.created_at}>{formatDate(n.created_at)}</time>
                  </p>
                </div>
                <div className="flex gap-2">
                  {n.link && (
                    <Link
                      href={n.link}
                      onClick={() => !n.read && void markRead(n.id)}
                      className="rounded-full px-3 py-1 text-sm text-primary hover:bg-surface"
                    >
                      Open
                    </Link>
                  )}
                  {!n.read && (
                    <button
                      type="button"
                      onClick={() => markRead(n.id)}
                      disabled={busy}
                      className="rounded-full px-3 py-1 text-sm hover:bg-surface"
                    >
                      Mark as read<span className="sr-only">: {n.title}</span>
                    </button>
                  )}
                </div>
              </div>
            </li>
          ))}
        </ul>
      )}
      {next && (
        <div className="mt-4">
          <Button variant="secondary" onClick={older} disabled={busy}>
            Show older
          </Button>
        </div>
      )}
    </section>
  );
}

function Preferences({ initial }: { initial: NotificationPreference[] }) {
  const [prefs, setPrefs] = useState(initial);
  const [error, setError] = useState<string | null>(null);
  const [saved, setSaved] = useState<string | null>(null);

  async function toggle(p: NotificationPreference, channel: "in_app" | "email") {
    const nextPref = { ...p, [channel]: !p[channel] };
    const before = prefs;
    // Optimistic, so the checkbox reflects the click immediately; restored if the save fails.
    setPrefs((all) => all.map((x) => (x.kind === p.kind ? nextPref : x)));
    setError(null);
    setSaved(null);
    try {
      const fresh = await api.setNotificationPreference({
        kind: p.kind,
        in_app: nextPref.in_app,
        email: nextPref.email,
      });
      setPrefs(fresh);
      setSaved(`Saved your choice for ${p.label.toLowerCase()}.`);
    } catch (err) {
      setPrefs(before);
      setError(errorMessage(err));
    }
  }

  return (
    <Card>
      <h2 className="text-xl font-semibold">What we notify you about</h2>
      <p className="mt-1 text-sm text-ink-muted">
        Choose where each kind of notification goes. Emails go to your confirmed address. Security notices are always
        on, and product news stays off unless you turn it on.
      </p>
      <div className="mt-2">
        {error && <FormMessage kind="error">{error}</FormMessage>}
        {saved && <FormMessage kind="success">{saved}</FormMessage>}
      </div>
      <table className="mt-4 w-full text-start text-sm">
        <caption className="sr-only">Notification preferences</caption>
        <thead>
          <tr className="border-b border-line">
            <th scope="col" className="py-2 text-start font-semibold">
              Kind
            </th>
            <th scope="col" className="w-20 py-2 text-center font-semibold">
              In app
            </th>
            <th scope="col" className="w-20 py-2 text-center font-semibold">
              Email
            </th>
          </tr>
        </thead>
        <tbody>
          {prefs.map((p) => (
            <tr key={p.kind} className="border-b border-line align-top">
              <th scope="row" className="py-3 pe-3 text-start font-normal">
                <span className="block font-medium">{p.label}</span>
                <span className="text-ink-muted">{p.description}</span>
              </th>
              {(["in_app", "email"] as const).map((channel) => (
                <td key={channel} className="py-3 text-center">
                  <input
                    type="checkbox"
                    className="h-5 w-5"
                    checked={p[channel]}
                    disabled={p.required}
                    onChange={() => toggle(p, channel)}
                    aria-label={`${p.label}: ${channel === "in_app" ? "in app" : "email"}`}
                  />
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </Card>
  );
}
