import type { Metadata } from "next";
import type { ReactNode } from "react";

export const metadata: Metadata = {
  title: "Discover",
  description:
    "Choose a free Big Five personality assessment, a career interests profile or leadership preferences.",
  alternates: { canonical: "/discover" },
};

export default function DiscoverLayout({ children }: { children: ReactNode }) {
  return children;
}
