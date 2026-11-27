import type { Metadata } from "next";
import type { ReactNode } from "react";

export const metadata: Metadata = {
  title: "Career exploration",
  description:
    "Bring together the work activities that appeal to you and how you tend to work, then explore real occupations. For reflection, not job matching.",
  alternates: { canonical: "/careers" },
};

export default function CareersLayout({ children }: { children: ReactNode }) {
  return children;
}
