"use client";

import { useEffect, useState } from "react";
import { ButtonLink, ErrorState, LoadingState } from "@/components/ui";
import { Card } from "@/components/ui";
import { api } from "@/lib/api";
import { errorMessage } from "@/lib/errors";
import { takeFragmentToken } from "@/lib/token";

type State = { status: "loading" } | { status: "done"; email: string } | { status: "error"; message: string };

export default function VerifyEmailPage() {
  const [state, setState] = useState<State>({ status: "loading" });

  useEffect(() => {
    (async () => {
      const token = takeFragmentToken("token");
      if (!token) {
        setState({ status: "error", message: "This link is incomplete. Please open the link from your email again." });
        return;
      }
      try {
        const user = await api.verifyEmail(token);
        setState({ status: "done", email: user.email });
      } catch (err) {
        setState({ status: "error", message: errorMessage(err) });
      }
    })();
  }, []);

  if (state.status === "loading") return <LoadingState label="Confirming your email" />;
  if (state.status === "error") {
    return (
      <ErrorState level={1} title="We couldn't confirm your email" message={state.message}
        action={<ButtonLink href="/login">Go to sign in</ButtonLink>} />
    );
  }
  return (
    <Card className="mx-auto max-w-md">
      <h1 className="text-2xl font-bold">Email confirmed</h1>
      <p className="mt-2 text-ink-muted">Thanks. {state.email} is confirmed and your account is ready.</p>
      <ButtonLink href="/login" className="mt-4">Sign in</ButtonLink>
    </Card>
  );
}
