"use client";

import type { JournalEntry, JournalKind, JournalList, JournalPrompts } from "@pdna/api-client";
import Link from "next/link";
import { type FormEvent, useState } from "react";
import { FormMessage } from "@/components/form";
import { Button, ButtonLink, Card, EmptyState, ErrorState, LoadingState } from "@/components/ui";
import { api } from "@/lib/api";
import { errorMessage } from "@/lib/errors";
import { downloadText, formatEntryDate, localToday, preview } from "@/lib/journal";
import { useRequireSignIn } from "@/lib/require-auth";
import { useAsync } from "@/lib/use-async";

interface Filters {
  q: string;
  tag: string;
  kind: JournalKind | "";
}

const NO_FILTERS: Filters = { q: "", tag: "", kind: "" };

function isFiltered(f: Filters) {
  return Boolean(f.q.trim() || f.tag || f.kind);
}

function load(f: Filters, cursor?: string | null): Promise<JournalList> {
  if (!isFiltered(f)) return api.journalEntries(cursor);
  return api.journalSearch({ q: f.q.trim() || null, tag: f.tag || null, kind: f.kind || null, cursor: cursor ?? null });
}

export default function JournalPage() {
  const auth = useRequireSignIn();
  const signedIn = auth.status === "signed-in";
  const [filters, setFilters] = useState<Filters>(NO_FILTERS);
  const base = useAsync(
    () => (signedIn ? Promise.all([api.journalPrompts(), api.journalTags()]) : Promise.resolve(null)),
    `journal:${signedIn}`,
  );
  const entries = useAsync(
    () => (signedIn ? load(filters) : Promise.resolve(null)),
    `entries:${signedIn}:${JSON.stringify(filters)}`,
  );

  if (!signedIn || base.status === "loading" || (base.status === "success" && !base.data))
    return <LoadingState label="Loading your journal" />;
  if (base.status === "error")
    return (
      <ErrorState level={1}
        title="We couldn't load your journal"
        message={errorMessage(base.error)}
        action={<Button onClick={base.reload}>Try again</Button>}
      />
    );
  const [prompts, tagList] = base.data!;

  return (
    <div className="space-y-8">
      <header className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="text-3xl font-bold">Journal</h1>
          <p className="mt-2 max-w-2xl text-ink-muted">{prompts.note}</p>
        </div>
        <ButtonLink href="/journal/new">New entry</ButtonLink>
      </header>

      <SearchForm
        prompts={prompts}
        tags={tagList.tags.map((t) => t.tag)}
        onSearch={setFilters}
        onClear={() => setFilters(NO_FILTERS)}
        filtered={isFiltered(filters)}
      />

      <section aria-labelledby="entries-heading" aria-busy={entries.status === "loading"}>
        <h2 id="entries-heading" className="sr-only">
          Entries
        </h2>
        {entries.status === "loading" || (entries.status === "success" && !entries.data) ? (
          <LoadingState label="Loading entries" />
        ) : entries.status === "error" ? (
          <ErrorState
            title="We couldn't load your entries"
            message={errorMessage(entries.error)}
            action={<Button onClick={entries.reload}>Try again</Button>}
          />
        ) : (
          <Entries key={JSON.stringify(filters)} first={entries.data!} filters={filters} prompts={prompts} />
        )}
      </section>

      <Manage />

      <aside aria-label="Getting support" className="rounded-card border border-line bg-muted p-4 text-sm">
        {prompts.support_note}
      </aside>
    </div>
  );
}

function SearchForm({
  prompts,
  tags,
  onSearch,
  onClear,
  filtered,
}: {
  prompts: JournalPrompts;
  tags: string[];
  onSearch: (f: Filters) => void;
  onClear: () => void;
  filtered: boolean;
}) {
  const [f, setF] = useState<Filters>(NO_FILTERS);
  function submit(e: FormEvent) {
    e.preventDefault();
    onSearch(f);
  }
  return (
    <form role="search" aria-label="Search your journal" onSubmit={submit} className="grid gap-3 sm:grid-cols-[1fr_auto_auto_auto]">
      <div>
        <label htmlFor="journal-q" className="sr-only">
          Search words
        </label>
        <input
          id="journal-q"
          type="search"
          placeholder="Search your entries"
          value={f.q}
          maxLength={200}
          onChange={(e) => setF({ ...f, q: e.target.value })}
          className="block min-h-12 w-full rounded-xl border border-line bg-surface px-4 py-2 text-base text-ink"
        />
      </div>
      <div>
        <label htmlFor="journal-kind" className="sr-only">
          Kind of entry
        </label>
        <select
          id="journal-kind"
          value={f.kind}
          onChange={(e) => setF({ ...f, kind: e.target.value as Filters["kind"] })}
          className="block min-h-12 w-full rounded-xl border border-line bg-surface px-3 text-ink"
        >
          <option value="">All kinds</option>
          {prompts.kinds.map((k) => (
            <option key={k.id} value={k.id}>
              {k.label}
            </option>
          ))}
        </select>
      </div>
      <div>
        <label htmlFor="journal-tag" className="sr-only">
          Tag
        </label>
        <select
          id="journal-tag"
          value={f.tag}
          onChange={(e) => setF({ ...f, tag: e.target.value })}
          className="block min-h-12 w-full rounded-xl border border-line bg-surface px-3 text-ink"
        >
          <option value="">All tags</option>
          {tags.map((t) => (
            <option key={t} value={t}>
              {t}
            </option>
          ))}
        </select>
      </div>
      <div className="flex gap-2">
        <Button type="submit">Search</Button>
        {filtered && (
          <Button
            type="button"
            variant="ghost"
            onClick={() => {
              setF(NO_FILTERS);
              onClear();
            }}
          >
            Clear
          </Button>
        )}
      </div>
    </form>
  );
}

function Entries({ first, filters, prompts }: { first: JournalList; filters: Filters; prompts: JournalPrompts }) {
  const [items, setItems] = useState<JournalEntry[]>(first.items);
  const [cursor, setCursor] = useState(first.next_cursor);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const label = (k: string) => prompts.kinds.find((x) => x.id === k)?.label ?? k;

  async function more() {
    setLoading(true);
    setError(null);
    try {
      const next = await load(filters, cursor);
      setItems((cur) => [...cur, ...next.items]);
      setCursor(next.next_cursor);
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setLoading(false);
    }
  }

  if (items.length === 0)
    return isFiltered(filters) ? (
      <EmptyState title="No matching entries" message="Try different words, or clear the search." />
    ) : (
      <EmptyState
        title="Your journal is empty"
        message="Write a few lines about today. There are prompts to help you start."
        action={<ButtonLink href="/journal/new">Write your first entry</ButtonLink>}
      />
    );

  return (
    <>
      <ul className="space-y-3">
        {items.map((e) => (
          <li key={e.id}>
            <Link
              href={`/journal/${e.id}`}
              className="block rounded-card border border-line bg-surface p-4 hover:bg-muted"
            >
              <span className="block text-sm text-ink-muted">
                {formatEntryDate(e.entry_date)} · {label(e.kind)}
                {e.mood ? ` · ${prompts.mood_scale[e.mood - 1]}` : ""}
              </span>
              <span className="block font-semibold">{e.title ?? label(e.kind)}</span>
              <span className="mt-1 block text-ink-muted">{preview(e.body)}</span>
              {e.tags.length > 0 && <span className="mt-1 block text-sm">Tags: {e.tags.join(", ")}</span>}
            </Link>
          </li>
        ))}
      </ul>
      {cursor && (
        <Button variant="secondary" className="mt-4" onClick={more} disabled={loading}>
          {loading ? "Loading…" : "Show more entries"}
        </Button>
      )}
      {error && <FormMessage kind="error">{error}</FormMessage>}
    </>
  );
}

function Manage() {
  const [busy, setBusy] = useState(false);
  const [confirming, setConfirming] = useState(false);
  const [message, setMessage] = useState<{ kind: "error" | "success"; text: string } | null>(null);

  async function exportAs(format: "markdown" | "json") {
    setBusy(true);
    setMessage(null);
    try {
      const text = await api.exportJournal(format);
      const ext = format === "json" ? "json" : "md";
      downloadText(text, `journal-${localToday()}.${ext}`, format === "json" ? "application/json" : "text/markdown");
    } catch (err) {
      setMessage({ kind: "error", text: errorMessage(err) });
    } finally {
      setBusy(false);
    }
  }

  async function deleteAll() {
    setBusy(true);
    setMessage(null);
    try {
      await api.deleteAllJournalEntries();
      window.location.reload();
    } catch (err) {
      setMessage({ kind: "error", text: errorMessage(err) });
      setBusy(false);
    }
  }

  return (
    <Card as="section" aria-labelledby="manage-heading">
      <h2 id="manage-heading" className="text-xl font-semibold">
        Your journal, your data
      </h2>
      <p className="mt-1 text-ink-muted">Download every entry, or delete your whole journal.</p>
      <div className="mt-4 flex flex-wrap gap-3">
        <Button variant="secondary" onClick={() => exportAs("markdown")} disabled={busy}>
          Download as Markdown
        </Button>
        <Button variant="secondary" onClick={() => exportAs("json")} disabled={busy}>
          Download as JSON
        </Button>
        {!confirming && (
          <Button variant="ghost" onClick={() => setConfirming(true)} disabled={busy}>
            Delete all entries
          </Button>
        )}
      </div>
      {confirming && (
        <div className="mt-4 rounded-card border border-line p-3" role="group" aria-label="Confirm deletion">
          <p>Delete every journal entry? This can&apos;t be undone. You may want to download them first.</p>
          <div className="mt-3 flex flex-wrap gap-3">
            <Button onClick={deleteAll} disabled={busy}>
              Yes, delete all entries
            </Button>
            <Button variant="secondary" onClick={() => setConfirming(false)} disabled={busy}>
              Cancel
            </Button>
          </div>
        </div>
      )}
      {message && <FormMessage kind={message.kind}>{message.text}</FormMessage>}
    </Card>
  );
}
