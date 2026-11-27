import type { Metadata } from "next";
import type { ReactNode } from "react";

export const metadata: Metadata = {
  title: "Send feedback",
  description: "Tell the PersonalityDNA team what isn't working or what you'd like.",
  robots: { index: false },
};

export default function FeedbackLayout({ children }: { children: ReactNode }) {
  return children;
}
