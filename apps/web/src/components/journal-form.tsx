"use client";

import type { JournalEntry, JournalEntryIn, JournalKind, JournalPrompts } from "@pdna/api-client";
import { type FormEvent, useState } from "react";
import { FormMessage, TextField } from "@/components/form";
import { Button } from "@/components/ui";
import { errorMessage } from "@/lib/errors";
import { localToday, parseTags } from "@/lib/journal";

const MAX_BODY = 20_000;

/** Write or edit a journal entry. Prompts are suggestions; nothing is required except the text. */
export function JournalForm({
  prompts,
  initial,
  initialKind,
  submitLabel,
  onSubmit,
  onCancel,
}: {
  prompts: JournalPrompts;
  initial?: JournalEntry;
  initialKind?: JournalKind;
  submitLabel: string;
  onSubmit: (body: JournalEntryIn) => Promise<void>;
  onCancel?: () => void;
}) {
  const [kind, setKind] = useState<JournalKind>(initial?.kind ?? initialKind ?? "daily");
  const [title, setTitle] = useState(initial?.title ?? "");
  const [body, setBody] = useState(initial?.body ?? "");
  const [mood, setMood] = useState<number | null>(initial?.mood ?? null);
  const [tags, setTags] = useState(initial?.tags.join(", ") ?? "");
  const [date, setDate] = useState(initial?.entry_date ?? localToday());
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const current = prompts.kinds.find((k) => k.id === kind) ?? prompts.kinds[0]!;

  async function submit(e: FormEvent) {
    e.preventDefault();
    if (!body.trim()) {
      setError("Write something before saving.");
      return;
    }
    setSaving(true);
    setError(null);
    try {
      await onSubmit({ kind, title: title.trim() || null, body, mood, tags: parseTags(tags), entry_date: date });
    } catch (err) {
      setError(errorMessage(err));
      setSaving(false);
    }
  }

  return (
    <form onSubmit={submit} className="space-y-6" noValidate>
      <fieldset>
        <legend className="font-medium">Kind of entry</legend>
        <div className="mt-2 flex flex-wrap gap-2">
          {prompts.kinds.map((k) => (
            <label key={k.id} className="flex items-center gap-2 rounded-full border border-line px-3 py-1.5 text-sm">
              <input type="radio" name="kind" value={k.id} checked={kind === k.id} onChange={() => setKind(k.id)} />
              {k.label}
            </label>
          ))}
        </div>
      </fieldset>

      <div className="rounded-card border border-line bg-muted p-4">
        <p className="font-semibold">Prompts to get you started</p>
        <ul className="mt-1 list-disc space-y-1 ps-5 text-sm">
          {current.prompts.map((p) => (
            <li key={p}>{p}</li>
          ))}
        </ul>
      </div>

      <TextField
        id="journal-date"
        label="Date"
        type="date"
        value={date}
        max={localToday()}
        onChange={(e) => setDate(e.target.value)}
        required
      />
      <TextField
        id="journal-title"
        label="Title (optional)"
        value={title}
        maxLength={200}
        onChange={(e) => setTitle(e.target.value)}
      />
      <div>
        <label htmlFor="journal-body" className="block font-medium">
          Your entry
        </label>
        <textarea
          id="journal-body"
          value={body}
          onChange={(e) => setBody(e.target.value)}
          maxLength={MAX_BODY}
          rows={10}
          className="mt-1 block w-full rounded-card border border-line bg-surface p-3 text-ink"
          aria-describedby="journal-body-hint"
        />
        <p id="journal-body-hint" className="mt-1 text-sm text-ink-muted">
          Only you can read this. It is encrypted when stored.
          {body.length > MAX_BODY - 1000 && ` ${MAX_BODY - body.length} characters left.`}
        </p>
      </div>

      <fieldset>
        <legend className="font-medium">Mood (optional)</legend>
        <div className="mt-2 flex flex-wrap gap-2">
          {prompts.mood_scale.map((label, i) => (
            <label key={label} className="flex items-center gap-2 rounded-full border border-line px-3 py-1.5 text-sm">
              <input type="radio" name="mood" checked={mood === i + 1} onChange={() => setMood(i + 1)} />
              {label}
            </label>
          ))}
          {mood !== null && (
            <Button type="button" variant="ghost" onClick={() => setMood(null)}>
              Clear mood
            </Button>
          )}
        </div>
      </fieldset>

      <TextField
        id="journal-tags"
        label="Tags (optional)"
        hint="Separate tags with commas, for example: work, family."
        value={tags}
        onChange={(e) => setTags(e.target.value)}
      />

      {error && <FormMessage kind="error">{error}</FormMessage>}
      <div className="flex flex-wrap gap-3">
        <Button type="submit" disabled={saving}>
          {saving ? "Saving…" : submitLabel}
        </Button>
        {onCancel && (
          <Button type="button" variant="secondary" onClick={onCancel} disabled={saving}>
            Cancel
          </Button>
        )}
      </div>
    </form>
  );
}
