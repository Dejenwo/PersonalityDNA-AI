import type { Metadata, Viewport } from "next";
import { SiteFooter, SiteHeader } from "@/components/site-chrome";
import { AttributionCapture } from "@/components/growth-tracking";
import { SkipLink } from "@/components/skip-link";
import { I18nProvider } from "@/i18n/provider";
import { AuthProvider } from "@/lib/auth";
import { SITE_NAME, SITE_URL } from "@/lib/site";
import "./globals.css";

const DESCRIPTION =
  "Discover yourself, understand others and grow, with a research-based Big Five personality assessment.";

export const metadata: Metadata = {
  metadataBase: new URL(SITE_URL),
  title: { default: SITE_NAME, template: `%s · ${SITE_NAME}` },
  description: DESCRIPTION,
  applicationName: SITE_NAME,
  openGraph: {
    type: "website",
    siteName: SITE_NAME,
    title: SITE_NAME,
    description: DESCRIPTION,
    locale: "en",
    url: "/",
  },
  twitter: { card: "summary", title: SITE_NAME, description: DESCRIPTION },
  formatDetection: { email: false, address: false, telephone: false },
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
          <AttributionCapture />
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
