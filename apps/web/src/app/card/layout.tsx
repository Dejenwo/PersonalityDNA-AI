import type { Metadata } from "next";
import type { ReactNode } from "react";

export const metadata: Metadata = {
  title: "Shared personality card",
  robots: { index: false, follow: false },
  referrer: "no-referrer",
};

export default function CardLayout({ children }: { children: ReactNode }) {
  return children;
}
