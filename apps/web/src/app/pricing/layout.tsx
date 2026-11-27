import type { Metadata } from "next";
import type { ReactNode } from "react";

export const metadata: Metadata = {
  title: "Pricing",
  description:
    "Free and Premium plans for PersonalityDNA AI. Start with a free Big Five assessment; upgrade only if you want more.",
  alternates: { canonical: "/pricing" },
};

export default function PricingLayout({ children }: { children: ReactNode }) {
  return children;
}
