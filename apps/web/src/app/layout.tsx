import type { Metadata, Viewport } from "next";
import { SiteFooter, SiteHeader } from "@/components/site-chrome";
import { SkipLink } from "@/components/skip-link";
import { I18nProvider } from "@/i18n/provider";
import { AuthProvider } from "@/lib/auth";
import "./globals.css";

export const metadata: Metadata = {
  title: { default: "PersonalityDNA AI", template: "%s · PersonalityDNA AI" },
  description: "Discover yourself, understand others and grow, with a research-based Big Five personality assessment.",
};

export const viewport: Viewport = {
  themeColor: [
    { media: "(prefers-color-scheme: light)", color: "#fbfaf7" },
    { media: "(prefers-color-scheme: dark)", color: "#0e1117" },
  ],
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" dir="ltr">
      <body className="bg-bg text-ink antialiased">
        <I18nProvider>
          <SkipLink />
          <AuthProvider>
            <SiteHeader />
            <main id="main" className="mx-auto max-w-5xl px-4 py-8">
              {children}
            </main>
            <SiteFooter />
          </AuthProvider>
        </I18nProvider>
      </body>
    </html>
  );
}
