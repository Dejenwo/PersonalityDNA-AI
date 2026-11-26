"use client";

import { Button, ErrorState } from "@/components/ui";

export default function GlobalError({ reset }: { error: Error; reset: () => void }) {
  return (
    <ErrorState
      title="Something went wrong"
      message="An unexpected error occurred. Your saved answers are safe."
      action={<Button onClick={reset}>Try again</Button>}
    />
  );
}
